#!/usr/bin/env python3
"""Acceptance scenarios for game-lib. Each scenario configures a scratch CMake
project and asserts something about the result. Python 3.11+, stdlib only."""
import argparse, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENARIOS = {}

sys.path.insert(0, str(ROOT / "tools"))
import vendor

def scenario(fn):
    SCENARIOS[fn.__name__.replace("_", "-")] = fn
    return fn

def cmake(src, build, *args, expect_ok=True):
    """Configure `src` into `build`. Returns CompletedProcess."""
    cp = subprocess.run(
        ["cmake", "-S", str(src), "-B", str(build), "-DCMAKE_BUILD_TYPE=Debug", *args],
        capture_output=True, text=True)
    if expect_ok and cp.returncode != 0:
        raise AssertionError(f"configure failed:\n{cp.stdout}\n{cp.stderr}")
    return cp

def build(build_dir, *args):
    cp = subprocess.run(["cmake", "--build", str(build_dir), *args],
                        capture_output=True, text=True)
    if cp.returncode != 0:
        raise AssertionError(f"build failed:\n{cp.stdout}\n{cp.stderr}")
    return cp

@scenario
def smoke():
    """game-lib configures and builds as a top-level project."""
    with tempfile.TemporaryDirectory() as d:
        cmake(ROOT, Path(d) / "b")
        build(Path(d) / "b")

@scenario
def vendor_check():
    """vendor.py check passes on a clean tree and fails on a modified one."""
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "vendor.py"), "check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, f"check failed on a clean tree:\n{r.stdout}\n{r.stderr}"

    victim = ROOT / "libs" / "stb" / "stb" / "stb_image.h"
    original = victim.read_bytes()
    try:
        victim.write_bytes(original + b"\n/* local edit */\n")
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "vendor.py"), "check"],
                           capture_output=True, text=True)
        assert r.returncode != 0, "check passed on a hand-edited vendored file"
        assert "tree_sha256" in (r.stdout + r.stderr)
    finally:
        victim.write_bytes(original)

@scenario
def vendor_release_tracking():
    """A tag resolve_latest matches must flow into both VERSION and the
    manifest rewrite, whether or not the table already tracked a `release`
    key, and must not be left stale (or falsely absent) when the resolved
    revision carries no tag at all. Exercised against fixtures only: no
    network call, no real `update` run, and tools/vendor.toml is never
    touched."""

    # --- Case 3: entry WITH an existing `release` key -------------------
    # rewrite_pin: moving to a new tagged release must update the release
    # line too -- Finding 1 was that only the commit hex got rewritten.
    with_release = (
        '[demo]\n'
        'url    = "https://example.invalid/x"\n'
        f'commit  = "{"a" * 40}"   # v1.0.0\n'
        'release = "v1.0.0"\n'
        'root    = "libs/demo"\n'
    )
    moved = vendor.rewrite_pin(with_release, "demo", "b" * 40, "v2.0.0")
    assert f'commit  = "{"b" * 40}"   # v2.0.0' in moved, moved
    assert 'release = "v2.0.0"' in moved, moved
    assert "v1.0.0" not in moved, moved

    # rewrite_pin: moving to an untagged (HEAD) revision must clear the
    # stale tag to "-", not leave the old release behind.
    untagged = vendor.rewrite_pin(with_release, "demo", "c" * 40, None)
    assert f'commit  = "{"c" * 40}"\n' in untagged, untagged
    assert 'release = "-"' in untagged, untagged
    assert "v1.0.0" not in untagged, untagged

    # --- Cases 1 & 2: entry with NO `release` key, followed by another
    # table -- catches both a stale-but-absent-key regression (fix round 2's
    # bug: VERSION got the tag, vendor.toml silently didn't) and an insertion
    # landing in the wrong table.
    no_release = (
        '[imgui]\n'
        'url     = "https://github.com/ocornut/imgui"\n'
        f'commit  = "{"a" * 40}"\n'
        'root    = "libs/imgui"\n'
        'subtree = "imgui"\n'
        'license = "LICENSE.txt"\n'
        'copy = [\n'
        '  "imgui.h",\n'
        ']\n'
        '\n'
        '[next]\n'
        'url    = "https://example.invalid/next"\n'
        f'commit  = "{"9" * 40}"\n'
        'root    = "libs/next"\n'
    )

    # Case 1: a tag WAS resolved -- a `release` key must be inserted right
    # after the commit line, and the following [next] table must be
    # completely untouched. Asserted against the FULL resulting text (not
    # just the changed line), which is what catches a wrong-table insertion.
    tagged = vendor.rewrite_pin(no_release, "imgui", "b" * 40, "v1.91.5")
    expected_tagged = (
        '[imgui]\n'
        'url     = "https://github.com/ocornut/imgui"\n'
        f'commit  = "{"b" * 40}"   # v1.91.5\n'
        'release = "v1.91.5"\n'
        'root    = "libs/imgui"\n'
        'subtree = "imgui"\n'
        'license = "LICENSE.txt"\n'
        'copy = [\n'
        '  "imgui.h",\n'
        ']\n'
        '\n'
        '[next]\n'
        'url    = "https://example.invalid/next"\n'
        f'commit  = "{"9" * 40}"\n'
        'root    = "libs/next"\n'
    )
    assert tagged == expected_tagged, tagged

    # Case 2: no tag was resolved -- no `release` key is inserted; the table
    # is byte-identical apart from the commit hex.
    untagged_no_release = vendor.rewrite_pin(no_release, "imgui", "c" * 40, None)
    expected_untagged = no_release.replace(f'"{"a" * 40}"', f'"{"c" * 40}"')
    assert untagged_no_release == expected_untagged, untagged_no_release
    assert "release" not in untagged_no_release

    # VERSION must agree with each of the two release-less cases above:
    # write_version always emits a `release:` line (defaulting to "-"), so
    # what matters is that the caller (cmd_update) fed it the right value.
    with tempfile.TemporaryDirectory(dir=ROOT) as d:
        root = Path(d)
        entry = {"url": "https://github.com/ocornut/imgui", "commit": "b" * 40,
                 "subtree": "imgui", "release": "v1.91.5"}   # case 1: tag resolved
        vendor.write_version(root, "imgui", entry, "cafef00d")
        assert vendor.read_version(root)["release"] == "v1.91.5"

    with tempfile.TemporaryDirectory(dir=ROOT) as d:
        root = Path(d)
        entry = {"url": "https://github.com/ocornut/imgui", "commit": "c" * 40,
                 "subtree": "imgui"}   # case 2: no tag resolved, no "release" key at all
        vendor.write_version(root, "imgui", entry, "deadbeef")
        assert vendor.read_version(root)["release"] == "-"

@scenario
def vendor_confinement():
    """resolve_paths must refuse an absolute or `..`-bearing root/subtree --
    that path is what cmd_update unconditionally shutil.rmtree()s, so a typo
    or a hostile manifest edit must be rejected before anything is deleted.
    No real entry is touched."""
    ok_root, ok_subtree = vendor.resolve_paths("stb", {"root": "libs/stb", "subtree": "stb"})
    assert ok_subtree == vendor.ROOT / "libs" / "stb" / "stb", ok_subtree

    for bad_entry, what in [
        ({"root": "/etc", "subtree": "passwd"}, "absolute root"),
        ({"root": "libs/evil", "subtree": "/etc"}, "absolute subtree"),
        ({"root": "../outside", "subtree": "x"}, ".. in root"),
        ({"root": "libs/evil", "subtree": "../../../../etc"}, ".. in subtree"),
    ]:
        try:
            vendor.resolve_paths("evil", bad_entry)
            raise AssertionError(f"resolve_paths accepted {what}: {bad_entry}")
        except SystemExit:
            pass

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenarios", nargs="*", choices=[*SCENARIOS, []], default=[])
    names = ap.parse_args().scenarios or list(SCENARIOS)
    failed = []
    for n in names:
        print(f"=== {n}", flush=True)
        try:
            SCENARIOS[n]()
            print(f"--- {n}: PASS", flush=True)
        except Exception as e:
            print(f"--- {n}: FAIL: {e}", flush=True)
            failed.append(n)
    print(f"\n{len(names) - len(failed)}/{len(names)} passed")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
