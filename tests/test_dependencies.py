"""The requirements files must match what the code really imports (stdlib-only checker, works offline)."""
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("check_dependencies", ROOT / "scripts" / "check_dependencies.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def test_code_imports_match_requirements():
    report, problems = checker.check()
    assert not problems, "\n".join(problems)


def test_runtime_requirements_are_minimal():
    names = checker.parse_requirements(ROOT / "requirements.txt")
    assert sorted(names) == ["cryptography", "pyside6-essentials"]


def test_no_stdlib_and_no_meta_package_anywhere():
    import sys
    for fname in checker.REQUIREMENT_FILES:
        for name in checker.parse_requirements(ROOT / fname):
            assert name.replace("-", "_") not in sys.stdlib_module_names, (fname, name)
            assert name != "pyside6", fname


def test_every_file_is_parseable_and_layered():
    assert "requirements.txt" in (ROOT / "requirements-test.txt").read_text()
    assert "requirements-test.txt" in (ROOT / "requirements-dev.txt").read_text()
    assert checker.parse_requirements(ROOT / "requirements-dev.txt") == ["pyinstaller"]
    # the application environment never gets an HTTP client from the requirement files it installs
    for fname in ("requirements.txt", "requirements-test.txt", "requirements-dev.txt"):
        text = (ROOT / fname).read_text().lower()
        for banned in ("requests", "urllib3", "httpx", "aiohttp", "pip-audit"):
            assert banned not in re.sub(r"#.*", "", text), (fname, banned)


def test_constraints_pin_every_declared_package_exactly():
    pinned = {}
    for line in (ROOT / "constraints.txt").read_text().splitlines():
        line = line.split("#")[0].strip()
        if line:
            name, _, version = line.partition("==")
            assert version, f"constraints must use == : {line}"
            pinned[checker.normalise(name)] = version
    for fname in ("requirements.txt", "requirements-test.txt", "requirements-dev.txt"):
        for name in checker.parse_requirements(ROOT / fname):
            assert name in pinned, f"{name} (from {fname}) has no tested pin in constraints.txt"


def _broken_copy(tmp_path, requirements_text):
    import shutil
    for name in ("main.py", "src", "tests", "scripts"):
        src = ROOT / name
        shutil.copytree(src, tmp_path / name, ignore=shutil.ignore_patterns("__pycache__")) if src.is_dir() else shutil.copy(src, tmp_path / name)
    (tmp_path / "requirements.txt").write_text(requirements_text)
    return tmp_path


@pytest.mark.parametrize("requirements,expected", [
    ("PySide6>=6.6\ncryptography>=42\n", "PySide6-Essentials"),             # meta-package instead of Essentials
    ("PySide6-Essentials>=6.6\n", "'cryptography' is imported"),            # missing runtime package
    ("PySide6-Essentials>=6.6\ncryptography>=42\nsqlite3\n", "standard-library"),   # stdlib listed
    ("PySide6-Essentials>=6.6\ncryptography>=42\ncryptography>=43\n", "listed twice"),
])
def test_checker_detects_real_problems(tmp_path, monkeypatch, requirements, expected):
    monkeypatch.setattr(checker, "ROOT", _broken_copy(tmp_path, requirements))
    monkeypatch.setattr(checker, "REQUIREMENT_FILES", ["requirements.txt"])
    _, problems = checker.check()
    assert any(expected in p for p in problems), problems


def test_checker_flags_a_new_qt_module(tmp_path, monkeypatch):
    root = _broken_copy(tmp_path, "PySide6-Essentials>=6.6\ncryptography>=42\n")
    (root / "src" / "gui" / "extra.py").write_text("from PySide6.QtWebEngineWidgets import QWebEngineView\n")
    monkeypatch.setattr(checker, "ROOT", root)
    monkeypatch.setattr(checker, "REQUIREMENT_FILES", ["requirements.txt"])
    _, problems = checker.check()
    assert any("QtWebEngineWidgets" in p for p in problems), problems
