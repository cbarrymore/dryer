"""Find source files and decide which language each one is written in.

The extensions and the skipped directories match crapper and mutator, with
`.cljd` added because dry4clj reads it and `.swift` added for Swift. C#
skips build output, generated files, and test projects as crapper does.
"""

import os
from pathlib import Path

EXTENSIONS = {
    ".clj": "clojure",
    ".cljc": "clojure",
    ".cljs": "clojure",
    ".cljd": "clojure",
    ".bb": "clojure",
    ".java": "java",
    ".go": "go",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".rs": "rust",
    ".py": "python",
    ".swift": "swift",
    ".cs": "csharp",
}

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".venv",
    "venv",
    "node_modules",
    "vendor",
    "target",
    "dist",
    "build",
    "out",
    "coverage",
    ".metrics",
    "testdata",
    "__pycache__",
    ".clj-kondo",
    "bin",
    "obj",
    ".vs",
    ".claude",
    "TestResults",
}

TEST_DIRS = {"test", "tests", "spec", "specs", "__tests__", "Tests"}

# One suffix list. Swift packages name XCTest files *Tests.swift.
_TEST_SUFFIXES = (
    "_test.go",
    "_test.clj",
    "_test.cljc",
    "_test.cljs",
    "_test.cljd",
    "_test.bb",
    ".test.ts",
    ".spec.ts",
    ".test.tsx",
    ".spec.tsx",
    ".test.mts",
    ".spec.mts",
    ".test.cts",
    ".spec.cts",
    "_test.py",
    "Tests.swift",
)

CSHARP_GENERATED_SUFFIXES = (".Designer.cs", ".g.cs", ".g.i.cs", ".generated.cs")


def language_of(path: str | Path) -> str | None:
    file_path = Path(path)
    name = file_path.name
    if name.endswith(".d.ts") or name.endswith(CSHARP_GENERATED_SUFFIXES):
        return None
    # EF Core writes Migrations/ and its model snapshot; nobody refactors them.
    if file_path.suffix == ".cs" and "Migrations" in file_path.parts:
        return None
    return EXTENSIONS.get(file_path.suffix)


def _csharp_test(file_path: Path) -> bool:
    """.NET test projects are named `*.Tests`, `*.UnitTests`, `*.IntegrationTest`..."""

    if file_path.suffix != ".cs":
        return False
    return any(part.endswith(("Test", "Tests")) for part in (file_path.stem, *file_path.parts[:-1]))


def is_test_file(path: str | Path) -> bool:
    file_path = Path(path)
    name = file_path.name
    if name == "conftest.py" or name.endswith(_TEST_SUFFIXES):
        return True
    if name.startswith("test_") and name.endswith(".py"):
        return True
    if _csharp_test(file_path):
        return True
    return any(part in TEST_DIRS for part in file_path.parts)


def _skipped_dir(name: str) -> bool:
    return name in SKIP_DIRS or name in TEST_DIRS


def _walk(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if root.is_file():
        return [root]
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if not _skipped_dir(name)]
        for name in filenames:
            path = Path(dirpath) / name
            if language_of(path) is None or is_test_file(path):
                continue
            found.append(path)
    return found


def iter_source_files(roots: list[Path]) -> list[Path]:
    files: set[Path] = set()
    for root in roots:
        for path in _walk(root):
            files.add(path.resolve())
    return sorted(files, key=lambda path: path.as_posix())
