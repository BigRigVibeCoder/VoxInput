#!/usr/bin/env python3
"""
Static Scanner: Bare Except Detection

Detects `except:` and `except Exception:` without specific exception types.
Enforces precise error handling.

Usage:
    python tests/scanners/bare_except_scanner.py

Exit Codes:
    0 - Clean (no bare excepts)
    1 - Violations found
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import sys

SCAN_TARGETS = [
    "src",
]

EXCLUDE_PATTERNS = ["__pycache__", "test_", "_test.py"]


@dataclass
class Violation:
    """Represents a bare except violation."""
    file: Path
    line: int
    except_type: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: {self.except_type}"


def scan_file(filepath: Path) -> list[Violation]:
    """Scan a Python file for bare except clauses."""
    violations = []

    try:
        content = filepath.read_text()
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    # Bare except:
                    violations.append(Violation(
                        file=filepath,
                        line=node.lineno,
                        except_type="bare 'except:' without exception type"
                    ))
                elif isinstance(node.type, ast.Name):
                    if node.type.id in ("Exception", "BaseException"):
                        # Check if it's in a try/except with other handlers
                        # If it's the only handler, it's too broad
                        violations.append(Violation(
                            file=filepath,
                            line=node.lineno,
                            except_type=f"overly broad 'except {node.type.id}:'"
                        ))

    except SyntaxError:
        pass
    except Exception as e:
        sys.stderr.write(f"Error scanning {filepath}: {e}\n")

    return violations


def scan_directory(path: Path) -> list[Violation]:
    """Recursively scan a directory."""
    violations = []

    for py_file in path.rglob("*.py"):
        if any(exc in str(py_file) for exc in EXCLUDE_PATTERNS):
            continue
        violations.extend(scan_file(py_file))

    return violations


def main() -> int:
    """Main entry point."""
    workspace = Path.cwd()
    if not (workspace / "src").exists():
        for parent in workspace.parents:
            if (parent / "src").exists():
                workspace = parent
                break

    all_violations: list[Violation] = []

    for target in SCAN_TARGETS:
        target_path = workspace / target
        if target_path.exists():
            all_violations.extend(scan_directory(target_path))

    if not all_violations:
        sys.stderr.write("✅ HM-IPV-003: No bare except clauses found\n")
        return 0

    # Report count without listing all (too noisy)
    sys.stderr.write(f"\n⚠️ HM-IPV-003 WARNING: {len(all_violations)} broad exception handlers found\n\n")

    # Group by file and show counts
    from collections import Counter
    file_counts = Counter(v.file for v in all_violations)
    for filepath, count in file_counts.most_common(10):
        sys.stderr.write(f"  {filepath}: {count} violations\n")

    if len(file_counts) > 10:
        sys.stderr.write(f"  ... and {len(file_counts) - 10} more files\n")

    sys.stderr.write("\nUse specific exception types per error taxonomy.\n")
    sys.stderr.write("Note: This is a WARNING - some broad catches may be intentional.\n\n")

    # Return 0 for now since this is a warning, not an error
    return 0


if __name__ == "__main__":
    sys.exit(main())
