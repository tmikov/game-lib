#!/usr/bin/env python3
"""Acceptance scenarios for game-lib. Each scenario configures a scratch CMake
project and asserts something about the result. Python 3.11+, stdlib only."""
import argparse, os, re, shutil, subprocess, sys, tempfile
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
    """game-lib configures and builds as a top-level project, then runs the
    one example that is headless and deterministic enough for CI to actually
    execute -- physics.c returns non-zero itself if the box never comes to
    rest in a plausible band, but nothing previously ran it to find out."""
    with tempfile.TemporaryDirectory() as d:
        b = Path(d) / "b"
        cmake(ROOT, b)
        build(b)
        exe = next(p for p in b.rglob("physics*")
                   if p.is_file() and os.access(p, os.X_OK) and p.suffix in ("", ".exe"))
        r = subprocess.run([str(exe)], capture_output=True, text=True)
        assert r.returncode == 0, f"physics example failed: {r.stdout}{r.stderr}"

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

@scenario
def consumer_isolation():
    """A consumer linking only stb_image builds, RUNS, and compiles nothing else."""
    with tempfile.TemporaryDirectory() as d:
        b = Path(d) / "b"
        cmake(ROOT / "tests" / "consumer-isolation", b, f"-DGAMELIB_ROOT={ROOT}")
        build(b)
        exe = next(p for p in b.rglob("consumer*")
                   if p.is_file() and os.access(p, os.X_OK) and p.suffix in ("", ".exe"))
        r = subprocess.run([str(exe)], capture_output=True, text=True)
        assert r.returncode == 0, f"consumer ran but failed: {r.stdout}{r.stderr}"

        objs = [p.as_posix() for p in b.rglob("*") if p.suffix in (".o", ".obj")]
        # An empty objs list would make every "forbidden" check below pass
        # vacuously (e.g. if the glob pattern or build layout ever changed).
        # Assert stb_image's own object exists first, so the scenario fails
        # loudly instead of silently proving nothing.
        assert any("gamelib_stb_image_impl" in o for o in objs), \
            f"stb_image's own object was never built -- scan found nothing: {objs}"
        for forbidden in ("sokol", "imgui", "miniaudio", "box2d"):
            leaked = [o for o in objs if forbidden in o]
            assert not leaked, f"{forbidden} objects built but never linked: {leaked}"

@scenario
def headless_dummy():
    """The dummy backend builds sokol_gfx and declares no sokol_app."""
    with tempfile.TemporaryDirectory() as d:
        b = Path(d) / "b"
        cp = cmake(ROOT, b, "-DGAMELIB_SOKOL_BACKEND=dummy")
        # Assert against the authoritative "game-lib targets:" summary line
        # (root CMakeLists.txt, printed from GAMELIB_DECLARED_TARGETS) rather
        # than raw stdout: a substring search over the whole configure log
        # also matches incidental diagnostic text (e.g. a STATUS message
        # explaining *why* sokol_app was skipped), which would fail the
        # scenario even when the target genuinely was not declared. A test
        # that can't find its summary line at all must fail loudly, not pass
        # silently.
        marker = "-- game-lib targets:"
        line = next((l for l in cp.stdout.splitlines() if l.startswith(marker)), None)
        assert line is not None, \
            f"configure output has no '{marker}' summary line to check:\n{cp.stdout}"
        declared = line[len(marker):].split()
        assert "sokol_app" not in declared, \
            f"sokol_app was declared under the dummy backend: {declared}"
        build(b, "--target", "gamelib_sokol_gfx")

@scenario
def headless_gfx_links():
    """The dummy backend must configure, BUILD and LINK an executable, not
    just a static library. target_link_libraries() on a STATIC library (what
    gamelib_sokol_gfx is) never invokes the linker, so building only static
    targets -- as headless_dummy above does, and as the headless CI job used
    to do -- could never catch a stray windowing dependency reaching
    sokol_gfx's PUBLIC link interface. tests/headless-gfx/ is a real
    add_executable() that calls sg_setup()/sg_shutdown() and is run here too,
    since the dummy backend needs no display."""
    with tempfile.TemporaryDirectory() as d:
        b = Path(d) / "b"
        cmake(ROOT / "tests" / "headless-gfx", b, f"-DGAMELIB_ROOT={ROOT}",
              "-DGAMELIB_SOKOL_BACKEND=dummy")
        build(b)
        exe = next(p for p in b.rglob("headless_gfx*")
                   if p.is_file() and os.access(p, os.X_OK) and p.suffix in ("", ".exe"))
        r = subprocess.run([str(exe)], capture_output=True, text=True)
        assert r.returncode == 0, f"headless_gfx ran but failed: {r.stdout}{r.stderr}"

@scenario
def sokol_backend_rejects_invalid():
    """An unsupported GAMELIB_SOKOL_BACKEND must fail configure with a clear
    error naming the bad value, not silently mispair into a wrong macro
    (a value that happens to sit in a macro slot, like SOKOL_GLCORE) and not
    crash on an out-of-range list(GET) (an outright nonsense value)."""
    for bad in ("SOKOL_GLCORE", "vulkan"):
        with tempfile.TemporaryDirectory() as d:
            b = Path(d) / "b"
            cp = cmake(ROOT, b, f"-DGAMELIB_SOKOL_BACKEND={bad}", expect_ok=False)
            assert cp.returncode != 0, \
                f"configure succeeded with GAMELIB_SOKOL_BACKEND={bad}"
            assert bad in (cp.stdout + cp.stderr), \
                f"error message did not name the bad value {bad}:\n{cp.stdout}{cp.stderr}"

@scenario
def compile_includes():
    """Every header-only library compiles under its documented include prefix."""
    with tempfile.TemporaryDirectory() as d:
        b = Path(d) / "b"
        cmake(ROOT / "tests" / "compile-includes", b, f"-DGAMELIB_ROOT={ROOT}")
        build(b)

@scenario
def shader_consumer():
    """gamelib_add_shader() must work when called from a genuine consumer's
    directory scope, not just from inside game-lib's own examples/. Every
    in-tree example calls it from a descendant of game-lib's own root
    CMakeLists.txt, which is exactly the scope where a directory-scoped
    set() of GAMELIB_SHDC / GAMELIB_SHDC_SLANG in cmake/GameLibShader.cmake
    stayed invisible while still passing every other scenario -- CMake
    variables propagate only downward through add_subdirectory, and a
    consumer's project is never a descendant of game-lib's.
    tests/shader-consumer/ is structured like tests/consumer-isolation/:
    game-lib is add_subdirectory()'d INTO it, not the reverse."""
    with tempfile.TemporaryDirectory() as d:
        b = Path(d) / "b"
        cmake(ROOT / "tests" / "shader-consumer", b, f"-DGAMELIB_ROOT={ROOT}")
        build(b)
        hdr = next(b.rglob("triangle.h"), None)
        assert hdr is not None and hdr.is_file(), \
            "gamelib_add_shader() did not produce triangle.h for an external consumer"

@scenario
def shader_incremental():
    """Editing the shader, or a file it @includes, regenerates the header.

    The sokol-shdc binary itself is also named in DEPENDS (re-vendoring the
    tool must regenerate every shader), but that edge is not exercised here:
    proving it portably would mean mutating a vendored binary's mtime in the
    working tree, which a test should not do. It was verified by hand for
    this round: touching tools/sokol-shdc/bin/linux/sokol-shdc's mtime and
    rebuilding regenerated triangle.h.
    """
    import time
    with tempfile.TemporaryDirectory() as d:
        b = Path(d) / "b"
        cmake(ROOT, b)
        build(b, "--target", "shader")
        hdr = next(b.rglob("triangle.h"))

        glsl = ROOT / "examples" / "shader" / "triangle.glsl"
        included = ROOT / "examples" / "shader" / "tint.glsl"
        original_glsl = glsl.read_text()
        original_included = included.read_text()
        try:
            first = hdr.stat().st_mtime_ns
            time.sleep(1.1)                      # coarse mtime granularity
            glsl.write_text(original_glsl + "\n// touch\n")
            build(b, "--target", "shader")
            second = hdr.stat().st_mtime_ns
            assert second != first, "editing the .glsl did not regenerate"

            time.sleep(1.1)
            included.write_text(original_included + "\n// touch\n")
            build(b, "--target", "shader")
            assert hdr.stat().st_mtime_ns != second, \
                "editing an @included file did not regenerate (DEPFILE not wired up)"
        finally:
            glsl.write_text(original_glsl)
            included.write_text(original_included)

PROHIBITED = ("include_directories(", "add_definitions(", "link_libraries(")
PROHIBITED_SET = ("CMAKE_C_FLAGS", "CMAKE_CXX_FLAGS", "CMAKE_C_STANDARD",
                  "CMAKE_CXX_STANDARD", "CMAKE_EXECUTABLE_SUFFIX")

@scenario
def no_global_state():
    """game-lib adds; it never changes. Cache comparison plus a command trace."""
    with tempfile.TemporaryDirectory() as d:
        b, trace = Path(d) / "b", Path(d) / "trace.txt"
        cmake(ROOT / "tests" / "no-global-state", b, f"-DGAMELIB_ROOT={ROOT}",
              "--trace-expand", f"--trace-redirect={trace}")

        # A trace line looks like "<path>(<line>):  <command>(<args>)". A naive
        # line.partition(":") breaks on Windows: the path starts "C:/...", so
        # the drive-letter colon is what gets split on, not the one after the
        # location -- "path" becomes just "C" and the startswith check below
        # never matches. Matching "(<digits>):" instead finds the real
        # location/command boundary regardless of colons earlier in the path.
        loc_re = re.compile(r"^(.*)\(\d+\):")
        ours = []
        for line in trace.read_text(errors="replace").splitlines():
            m = loc_re.match(line)
            if not m:
                continue
            path = Path(m.group(1))
            try:
                rel = path.relative_to(ROOT)
            except ValueError:
                continue                 # not under game-lib's own tree
            if "tests" in rel.parts:
                continue                 # the scenario's own CMakeLists.txt
            # Comparing Path objects (not str(ROOT)) also fixes the other
            # Windows failure mode: str(ROOT) is backslash-separated there
            # while CMake's trace output always uses forward slashes, so a
            # plain startswith() on strings would never match either.
            ours.append((path.as_posix(), line[m.end():]))

        assert ours, (
            "no game-lib-owned trace lines found at all -- either ROOT is "
            "wrong or the location-line regex stopped matching; every "
            "assertion below would otherwise pass vacuously")

        # Word-boundary matches: a naive substring check would flag the
        # correct, target-scoped commands game-lib uses throughout (e.g.
        # "target_include_directories(" contains "include_directories(" as a
        # literal substring) and every CMAKE_CXX_STANDARD-prefixed variable
        # name (e.g. CMAKE_CXX_STANDARD_REQUIRED) as a false positive.
        for cmd in PROHIBITED:
            pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(cmd))
            hits = [l for _, l in ours if pat.search(l)]
            assert not hits, f"prohibited {cmd} in game-lib: {hits[:3]}"
        for var in PROHIBITED_SET:
            pat = re.compile(r"set\(\s*" + re.escape(var) + r"(?![A-Za-z0-9_])")
            hits = [l for _, l in ours if pat.search(l)]
            assert not hits, f"game-lib set {var}: {hits[:3]}"
        # PARENT_SCOPE is legitimate inside a function (that is how CMake
        # functions return); it is banned at directory scope. Our only use is
        # gamelib_have_targets in cmake/GameLibLibrary.cmake -- plain
        # --trace-expand text carries only the expanded command (here
        # "set(_have_imgui_deps TRUE PARENT_SCOPE)"), not the enclosing
        # function's name, so the whitelist is keyed on that function's one
        # source file rather than a string that can never appear on these
        # lines. Confirmed by grep that no other set(... PARENT_SCOPE) exists
        # in that file, so this stays exactly as narrow as a name-based match.
        gamelib_library_cmake = (ROOT / "cmake" / "GameLibLibrary.cmake").as_posix()
        hits = [l for p, l in ours
                if "PARENT_SCOPE" in l and gamelib_library_cmake not in p]
        assert not hits, f"unexpected PARENT_SCOPE in game-lib: {hits[:3]}"


@scenario
def option_off():
    """A disabled library is not declared and its CMakeLists is never parsed."""
    with tempfile.TemporaryDirectory() as d:
        b, trace = Path(d) / "b", Path(d) / "trace.txt"
        cmake(ROOT / "tests" / "option-off", b, f"-DGAMELIB_ROOT={ROOT}",
              "--trace-expand", f"--trace-redirect={trace}")
        text = trace.read_text(errors="replace")
        # An empty (or truncated) trace file would make the assertion below
        # pass vacuously -- it only proves the string is absent, not that the
        # trace actually captured the configure.
        assert "add_subdirectory" in text, \
            f"trace file has no evidence of a configure at all: {text[:500]!r}"
        assert "libs/miniaudio/CMakeLists.txt" not in text, \
            "libs/miniaudio/CMakeLists.txt was parsed despite GAMELIB_MINIAUDIO=OFF"

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
