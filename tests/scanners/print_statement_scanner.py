#!/usr/bin/env python3
"""
Static Scanner: Forbidden print() Detection

NASA/JPL-style automated static analysis to prevent logging violations.
This scanner enforces that there are no print() commands in production code.

Usage:
    python tests/scanners/print_statement_scanner.py [--fix]

Exit Codes:
    0 - Clean (no violations)
    1 - Violations found

Rules:
    - All print() statements are forbidden in production code (src/)
    - Use logging functions or sys.stderr.write() for errors
    - Exception: file=sys.stderr is acceptable for fatal crash output
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys

# Components to scan (production code only)
SCAN_TARGETS = [
    "src",
]

# Patterns to exclude
EXCLUDE_PATTERNS = [
    "__pycache__",
    ".pyc",
    "test_",
    "_test.py",
]


@dataclass
class Violation:
    """Represents a print() violation."""
    file: Path
    line: int
    content: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: {self.content.strip()}"


def is_acceptable_print(line: str) -> bool:
    """Check if the print statement is acceptable."""
    # file=sys.stderr is allowed for fatal error output
    if "file=sys.stderr" in line:
        return True
    # Commented out prints are fine
    if re.match(r"^\s*#", line):
        return True
    return False


def scan_file(filepath: Path) -> list[Violation]:
    """Scan a Python file for print() violations."""
    violations = []

    try:
        content = filepath.read_text()
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            # Check for print( patterns
            if re.search(r"\bprint\s*\(", line):
                if not is_acceptable_print(line):
                    violations.append(Violation(
                        file=filepath,
                        line=i,
                        content=line
                    ))
    except Exception as e:
        sys.stderr.write(f"Error scanning {filepath}: {e}\n")

    return violations


def scan_directory(path: Path) -> list[Violation]:
    """Recursively scan a directory for print() violations."""
    violations = []

    if path.is_file() and path.suffix == ".py":
        violations.extend(scan_file(path))
    elif path.is_dir():
        for py_file in path.rglob("*.py"):
            # Skip excluded patterns
            if any(exc in str(py_file) for exc in EXCLUDE_PATTERNS):
                continue
            violations.extend(scan_file(py_file))

    return violations


def generate_fix(violation: Violation) -> str:
    """Generate the fix for a print() violation."""
    line = violation.content

    # Handle flush=True variant
    if "flush=True" in line:
        # Replace print(..., flush=True) with sys.stderr.write(...\n); sys.stderr.flush()
        line = re.sub(
            r'print\(([^)]+),\s*flush=True\)',
            r'sys.stderr.write(\1 + "\\n"); sys.stderr.flush()',
            line
        )
    else:
        # Replace print(f"...") with sys.stderr.write(f"...\n")
        line = re.sub(
            r'print\(f"([^"]*)"\)',
            r'sys.stderr.write(f"\1\\n")',
            line
        )
        line = re.sub(
            r'print\("([^"]*)"\)',
            r'sys.stderr.write("\1\\n")',
            line
        )

    return line


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Static Scanner: Detect forbidden print() statements"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Suggest fixes (does not auto-apply)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )
    args = parser.parse_args()

    # Find workspace root
    workspace = Path.cwd()
    if not (workspace / "src").exists():
        # Try parent directories
        for parent in workspace.parents:
            if (parent / "src").exists():
                workspace = parent
                break

    all_violations: list[Violation] = []

    # Scan all targets
    for target in SCAN_TARGETS:
        target_path = workspace / target
        if target_path.exists():
            all_violations.extend(scan_directory(target_path))

    if not all_violations:
        sys.stderr.write("✅ HM-IPV-005: No print() violations found\n")
        return 0

    # Report violations
    sys.stderr.write(f"\n❌ HM-IPV-005 VIOLATION: {len(all_violations)} forbidden print() statements found\n\n")

    for v in all_violations:
        sys.stderr.write(f"  {v}\n")
        if args.fix:
            fix = generate_fix(v)
            sys.stderr.write(f"    FIX: {fix.strip()}\n")

    sys.stderr.write("\nUse logging module or sys.stderr.write() instead.\n\n")

    return 1


if __name__ == "__main__":
    sys.exit(main())
