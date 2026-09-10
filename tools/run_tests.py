#!/usr/bin/env python3
"""Acceptance scenarios for game-lib. Each scenario configures a scratch CMake
project and asserts something about the result. Python 3.11+, stdlib only."""
import argparse, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENARIOS = {}

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
