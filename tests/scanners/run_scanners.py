#!/usr/bin/env python3
"""
Master Scanner Runner for VoxInput

Executes all static AST scanners in the `tests/scanners` directory
and aggregates the results. Exits with code 1 if any scanners fail.

Usage:
    python tests/scanners/run_scanners.py
"""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Run all scanners and aggregate results."""
    scanners_dir = Path(__file__).parent
    
    scanners = [
        "bare_except_scanner.py",
        "print_statement_scanner.py"
    ]
    
    all_passed = True
    print("========================================")
    print(" Running VoxInput AST Static Scanners ")
    print("========================================")
    
    for scanner in scanners:
        scanner_path = scanners_dir / scanner
        print(f"\n=> Running {scanner}...")
        
        result = subprocess.run(
            [sys.executable, str(scanner_path)],
            capture_output=True,
            text=True
        )
        
        # Print output (standard and error)
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            sys.stderr.write(result.stderr)
            
        if result.returncode != 0:
            print(f"❌ {scanner} FAILED.")
            all_passed = False
        else:
            print(f"✅ {scanner} PASSED.")
            
    print("\n========================================")
    if all_passed:
        print("🎉 ALL SCANNERS PASSED!")
        return 0
    else:
        print("💥 SCANNER SUITE FAILED.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
