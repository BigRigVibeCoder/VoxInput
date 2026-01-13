#!/usr/bin/env python3
import os
import subprocess
import sys
import time


def run_command_with_logging(cmd, env=None):
    """Run a command and return its exit code."""
    try:
        result = subprocess.run(
            cmd, 
            env=env, 
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr)
        return result.returncode
    except Exception as e:
        print(f"Error running command: {e}")
        return 1

def run_static_analysis():
    print("\n" + "="*80)
    print("STATIC ANALYSIS (Pre-Flight Checks)")
    print("="*80)
    
    env = os.environ.copy()
    
    # 1. Ruff (Linting)
    print("--> Running Ruff (Linting)...")
    cmd_ruff = [sys.executable, "-m", "ruff", "check", ".", "--config", "pyproject.toml"]
    start_r = time.time()
    ret_r = run_command_with_logging(cmd_ruff, env=env)
    dur_r = time.time() - start_r
    
    if ret_r != 0:
        print(f"!!! RUFF FAILED ({dur_r:.2f}s) !!!")
        print("    Fix linting errors before running safe code.")
        return False
    else:
        print(f"    Ruff Clean ({dur_r:.2f}s)")
        
    # 2. MyPy (Type Checking)
    print("--> Running MyPy (Type Safety)...")
    # We target specific source roots
    targets = [
        "src"
    ]
    cmd_mypy = [sys.executable, "-m", "mypy", "--config-file", "pyproject.toml"] + targets
    start_m = time.time()
    ret_m = run_command_with_logging(cmd_mypy, env=env)
    dur_m = time.time() - start_m

    if ret_m != 0:
        print(f"!!! MYPY FAILED ({dur_m:.2f}s) !!!")
        return False
    else:
        print(f"    MyPy Clean ({dur_m:.2f}s)")
        
    return True

def run_tests():
    print("\n" + "="*80)
    print("TEST EXECUTION")
    print("="*80)
    
    # Run pytest
    print("--> Running Pytest (Unit, Integration, E2E)...")
    cmd_pytest = [sys.executable, "-m", "pytest"]
    
    start_t = time.time()
    ret_t = run_command_with_logging(cmd_pytest)
    dur_t = time.time() - start_t
    
    if ret_t != 0:
        print(f"!!! TESTS FAILED ({dur_t:.2f}s) !!!")
        return False
    else:
        print(f"    ALL TESTS PASSED ({dur_t:.2f}s)")
        return True

if __name__ == "__main__":
    # 1. Pre-flight Checks
    if not run_static_analysis():
        sys.exit(1)
        
    # 2. Run Tests
    if not run_tests():
        sys.exit(1)
        
    print("\n✅ PRE-FLIGHT CHECKS & TESTS COMPLETE")
    sys.exit(0)
