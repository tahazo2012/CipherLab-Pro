"""Dependency checker: compares what the code IMPORTS with what the requirements files DECLARE.

    python scripts/check_dependencies.py            # print a report
    python scripts/check_dependencies.py --strict   # exit code 1 if anything is wrong (used by the test suite)

It needs only the standard library, so it also runs on a machine that is completely offline.
Checks:
  1. every third-party package imported by the application (main.py + src/) is declared in requirements.txt;
  2. nothing in requirements*.txt is a standard-library module (those must never be listed);
  3. no package is declared twice, and no requirements file lists the GUI meta-package "PySide6"
     (it drags in WebEngine/Addons/Pdf - use PySide6-Essentials);
  4. the Qt modules imported are ones that PySide6-Essentials contains.
"""
from __future__ import annotations

import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIREMENT_FILES = ["requirements.txt", "requirements-test.txt", "requirements-dev.txt", "requirements-audit.txt"]
# import name -> distribution names (normalised) that provide it
IMPORT_TO_DIST = {
    "PySide6": {"pyside6-essentials"},
    "shiboken6": {"shiboken6", "pyside6-essentials"},
    "cryptography": {"cryptography"},
    "pytest": {"pytest"},
}
# Qt modules the application may import. All of them ship in PySide6-Essentials. To use another Qt module,
# first confirm it is in Essentials (otherwise the requirement would have to change), then add it here.
ESSENTIALS_QT_MODULES = {"QtCore", "QtGui", "QtWidgets"}


def normalise(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_requirements(path: Path) -> list[str]:
    """Distribution names declared in one requirements file (options such as -r / -c are skipped)."""
    names = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#")[0].strip()
        if not line or line.startswith("-"):
            continue
        match = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", line)
        if match:
            names.append(normalise(match.group()))
    return names


def imports_of(files: list[Path]) -> tuple[dict[str, set[str]], set[str]]:
    """(third-party import roots -> files using them, set of PySide6 submodules used)."""
    third: dict[str, set[str]] = defaultdict(set)
    qt: set[str] = set()
    for f in files:
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                mods = [node.module]
            else:
                continue
            for m in mods:
                root = m.split(".")[0]
                if root in sys.stdlib_module_names or root in ("src", "__future__"):
                    continue
                third[root].add(f.relative_to(ROOT).as_posix())
                if root == "PySide6" and "." in m:
                    qt.add(m.split(".")[1])
    return third, qt


def check() -> tuple[list[str], list[str]]:
    """Return (report lines, problems)."""
    problems: list[str] = []
    runtime_files = [ROOT / "main.py", *sorted((ROOT / "src").rglob("*.py"))]
    test_files = sorted((ROOT / "tests").rglob("*.py"))
    declared = {name: parse_requirements(ROOT / name) for name in REQUIREMENT_FILES if (ROOT / name).exists()}
    runtime_declared = set(declared.get("requirements.txt", []))
    all_declared = {d for names in declared.values() for d in names}

    third, qt_used = imports_of(runtime_files)
    report = ["Runtime third-party imports:"]
    for root, users in sorted(third.items()):
        providers = IMPORT_TO_DIST.get(root, {normalise(root)})
        ok = bool(providers & runtime_declared)
        report.append(f"  {root:14} used by {len(users):2} file(s)  declared: {'yes' if ok else 'NO'}")
        if not ok:
            problems.append(f"'{root}' is imported by the application but not declared in requirements.txt")
    extra = qt_used - ESSENTIALS_QT_MODULES
    report.append(f"Qt modules used: {', '.join(sorted(qt_used)) or '-'}")
    if extra:
        problems.append(f"Qt module(s) {sorted(extra)} are not on the PySide6-Essentials allow-list (see check_dependencies.py)")

    test_third, _ = imports_of(test_files)
    for root in sorted(test_third):
        providers = IMPORT_TO_DIST.get(root, {normalise(root)})
        if not (providers & all_declared):
            problems.append(f"'{root}' is imported by the tests but not declared in any requirements file")

    for fname, names in declared.items():
        for name in names:
            if name.replace("-", "_") in sys.stdlib_module_names:
                problems.append(f"{fname}: '{name}' is a standard-library module and must not be listed")
            if name == "pyside6":
                problems.append(f"{fname}: use PySide6-Essentials instead of the PySide6 meta-package")
        if len(names) != len(set(names)):
            problems.append(f"{fname}: a package is listed twice")
    seen: dict[str, str] = {}
    for fname in ("requirements.txt", "requirements-test.txt", "requirements-dev.txt"):
        for name in declared.get(fname, []):
            if name in seen:
                problems.append(f"'{name}' is declared in both {seen[name]} and {fname}")
            seen[name] = fname
    report.append("Declared: " + "; ".join(f"{f}: {', '.join(n) or '-'}" for f, n in declared.items()))
    return report, problems


def main() -> int:
    report, problems = check()
    print("\n".join(report))
    print("\nPROBLEMS:" if problems else "\nNo problems found.")
    for p in problems:
        print(" -", p)
    return 1 if (problems and "--strict" in sys.argv) else 0


if __name__ == "__main__":
    sys.exit(main())
