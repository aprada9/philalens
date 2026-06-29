#!/usr/bin/env python3
"""Ensure meaningful changes keep Philalens agent context fresh."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


CONTEXT_PATHS = (
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "GPT.md",
    "README.md",
    "docs/ai/",
    "docs/product-brief.md",
    "docs/architecture.md",
    "docs/data-strategy.md",
    "docs/roadmap.md",
)

TRIGGER_PATHS = (
    "backend/",
    "docs/",
    "scripts/",
    ".github/",
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "GPT.md",
    ".env.example",
    ".gitignore",
)

IGNORED_PATHS = (
    "data/.gitkeep",
    "notebooks/.gitkeep",
)


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def git_ref_exists(ref: str) -> bool:
    result = run_git(["rev-parse", "--verify", "--quiet", ref])
    return result.returncode == 0


def changed_files(base: str | None, head: str) -> list[str]:
    paths: list[str] = []

    if base and git_ref_exists(base):
        result = run_git(["diff", "--name-only", f"{base}...{head}"])
        if result.returncode == 0:
            paths.extend(clean_paths(result.stdout))

        if not paths:
            result = run_git(["diff", "--name-only", base, head])
            if result.returncode == 0:
                paths.extend(clean_paths(result.stdout))

    staged = run_git(["diff", "--name-only", "--cached"])
    if staged.returncode == 0 and staged.stdout.strip():
        paths.extend(clean_paths(staged.stdout))

    unstaged = run_git(["diff", "--name-only"])
    if unstaged.returncode == 0 and unstaged.stdout.strip():
        paths.extend(clean_paths(unstaged.stdout))

    untracked = run_git(["ls-files", "--others", "--exclude-standard"])
    if untracked.returncode == 0 and untracked.stdout.strip():
        paths.extend(clean_paths(untracked.stdout))

    return sorted(dict.fromkeys(paths))


def clean_paths(output: str) -> list[str]:
    return [
        line.strip()
        for line in output.splitlines()
        if line.strip() and line.strip() not in IGNORED_PATHS
    ]


def matches_any(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=None, help="Base git ref for comparison.")
    parser.add_argument("--head", default="HEAD", help="Head git ref for comparison.")
    args = parser.parse_args()

    if not Path("AGENTS.md").exists():
        print("AGENTS.md is missing. Run this script from the repository root.", file=sys.stderr)
        return 2

    paths = changed_files(args.base, args.head)
    if not paths:
        print("No changed files detected; context guard passed.")
        return 0

    triggering_changes = [path for path in paths if matches_any(path, TRIGGER_PATHS)]
    context_updates = [path for path in paths if matches_any(path, CONTEXT_PATHS)]

    if triggering_changes and not context_updates:
        print("Context guard failed.")
        print()
        print("Meaningful project files changed, but no agent/product context file changed.")
        print("Update at least one relevant context document before finishing.")
        print()
        print("Changed files:")
        for path in triggering_changes:
            print(f"  - {path}")
        print()
        print("Typical files to update:")
        for path in CONTEXT_PATHS:
            print(f"  - {path}")
        return 1

    print("Context guard passed.")
    if context_updates:
        print("Context updates detected:")
        for path in context_updates:
            print(f"  - {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
