#!/usr/bin/env python3
"""Produce a read-only, secret-conscious inventory of a software project."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

SKIP_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode", "node_modules", "vendor",
    "dist", "build", "target", "coverage", ".next", ".nuxt", ".cache",
    ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache",
}

SECRET_NAMES = {
    ".env", ".env.local", ".env.production", ".npmrc", ".pypirc",
    "credentials.json", "secrets.json", "id_rsa", "id_ed25519",
}

LANGUAGE_EXTENSIONS = {
    ".py": "Python", ".js": "JavaScript", ".mjs": "JavaScript",
    ".cjs": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript/React",
    ".jsx": "JavaScript/React", ".java": "Java", ".kt": "Kotlin",
    ".kts": "Kotlin", ".cs": "C#", ".go": "Go", ".rs": "Rust",
    ".c": "C", ".h": "C/C++", ".cc": "C++", ".cpp": "C++",
    ".hpp": "C++", ".swift": "Swift", ".dart": "Dart", ".php": "PHP",
    ".rb": "Ruby", ".scala": "Scala", ".sh": "Shell", ".ps1": "PowerShell",
    ".sql": "SQL", ".vue": "Vue", ".svelte": "Svelte", ".ex": "Elixir",
    ".exs": "Elixir", ".erl": "Erlang", ".fs": "F#", ".fsx": "F#",
}

MANIFESTS = {
    "package.json", "pnpm-workspace.yaml", "pyproject.toml", "requirements.txt",
    "Pipfile", "poetry.lock", "Cargo.toml", "go.mod", "pom.xml",
    "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts",
    "composer.json", "Gemfile", "mix.exs", "pubspec.yaml", "Package.swift",
    "CMakeLists.txt", "Makefile", "justfile", "Dockerfile", "docker-compose.yml",
    "docker-compose.yaml", "compose.yml", "compose.yaml",
}

LOCKFILES = {
    "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml",
    "bun.lock", "bun.lockb", "uv.lock", "Pipfile.lock", "poetry.lock",
    "Cargo.lock", "go.sum", "composer.lock", "Gemfile.lock", "pubspec.lock",
}

INSTRUCTION_FILES = {
    "AGENTS.md", "CLAUDE.md", "CLAUDE.local.md", "GEMINI.md", "CONTRIBUTING.md",
    "DEVELOPING.md", "README.md", "SECURITY.md", "CODE_OF_CONDUCT.md",
}

TEST_DIR_NAMES = {"test", "tests", "spec", "specs", "e2e", "integration", "__tests__"}


def is_secret(path: Path) -> bool:
    name = path.name.lower()
    return name in SECRET_NAMES or name.startswith(".env.") or "secret" in name or "credential" in name


def walk_files(root: Path, max_files: int) -> list[Path]:
    files: list[Path] = []
    for current, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        base = Path(current)
        for name in sorted(names):
            path = base / name
            if is_secret(path):
                continue
            files.append(path)
            if len(files) >= max_files:
                return files
    return files


def infer_commands(root: Path, present: set[str]) -> list[str]:
    commands: list[str] = []
    if "package.json" in present:
        if "pnpm-lock.yaml" in present:
            commands += ["pnpm install", "pnpm test", "pnpm run build"]
        elif "yarn.lock" in present:
            commands += ["yarn install", "yarn test", "yarn build"]
        else:
            commands += ["npm install", "npm test", "npm run build"]
    if "pyproject.toml" in present or "requirements.txt" in present:
        commands += ["python -m pytest"]
    if "Cargo.toml" in present:
        commands += ["cargo test", "cargo clippy --all-targets --all-features"]
    if "go.mod" in present:
        commands += ["go test ./..."]
    if "pom.xml" in present:
        commands += ["mvn test"]
    if "build.gradle" in present or "build.gradle.kts" in present:
        commands += ["./gradlew test"]
    if "composer.json" in present:
        commands += ["composer install"]
    if "Gemfile" in present:
        commands += ["bundle install", "bundle exec rspec"]
    if "pubspec.yaml" in present:
        commands += ["flutter test"]
    return list(dict.fromkeys(commands))


def inventory(root: Path, max_files: int) -> dict[str, Any]:
    files = walk_files(root, max_files)
    language_counts: Counter[str] = Counter()
    manifests: list[str] = []
    lockfiles: list[str] = []
    instructions: list[str] = []
    ci_files: list[str] = []
    test_dirs: set[str] = set()

    for path in files:
        rel = path.relative_to(root).as_posix()
        language = LANGUAGE_EXTENSIONS.get(path.suffix.lower())
        if language:
            language_counts[language] += 1
        if path.name in MANIFESTS:
            manifests.append(rel)
        if path.name in LOCKFILES:
            lockfiles.append(rel)
        if path.name in INSTRUCTION_FILES:
            instructions.append(rel)
        if ".github/workflows/" in rel or rel.startswith(".gitlab-ci") or path.name in {"Jenkinsfile", "azure-pipelines.yml", "bitbucket-pipelines.yml"}:
            ci_files.append(rel)
        for parent in path.relative_to(root).parents:
            if parent.name.lower() in TEST_DIR_NAMES:
                test_dirs.add(parent.as_posix())

    root_names = {p.name for p in files if p.parent == root}
    return {
        "root": str(root.resolve()),
        "files_scanned": len(files),
        "scan_truncated": len(files) >= max_files,
        "languages_by_file_count": dict(language_counts.most_common()),
        "manifests": sorted(manifests),
        "lockfiles": sorted(lockfiles),
        "instruction_files": sorted(instructions),
        "ci_files": sorted(ci_files),
        "test_directories": sorted(test_dirs),
        "likely_commands_not_executed": infer_commands(root, root_names),
        "notes": [
            "Secret-like filenames and common generated/vendor directories were skipped.",
            "Suggested commands are heuristics and were not executed.",
        ],
    }


def render_text(data: dict[str, Any]) -> str:
    lines = [f"Project: {data['root']}", f"Files scanned: {data['files_scanned']}"]
    if data["scan_truncated"]:
        lines.append("Warning: scan reached the file limit")
    for title, key in [
        ("Languages", "languages_by_file_count"),
        ("Manifests", "manifests"),
        ("Lockfiles", "lockfiles"),
        ("Instruction files", "instruction_files"),
        ("CI files", "ci_files"),
        ("Test directories", "test_directories"),
        ("Likely commands (not executed)", "likely_commands_not_executed"),
    ]:
        lines.append(f"\n{title}:")
        value = data[key]
        if isinstance(value, dict):
            lines.extend(f"  - {name}: {count}" for name, count in value.items())
        else:
            lines.extend(f"  - {item}" for item in value) if value else lines.append("  - none detected")
    lines.append("\nNotes:")
    lines.extend(f"  - {item}" for item in data["notes"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=".", help="Project directory")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--max-files", type=int, default=20000, help="Maximum files to scan")
    args = parser.parse_args()

    root = Path(args.project).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        parser.error(f"not a directory: {root}")
    if args.max_files < 1:
        parser.error("--max-files must be at least 1")

    data = inventory(root, args.max_files)
    print(json.dumps(data, indent=2, ensure_ascii=False) if args.json else render_text(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
