"""The do-not-call list: one number per line. Anyone who asks not to be called again goes here."""
from __future__ import annotations

from pathlib import Path


def normalize(number: str) -> str:
    return "".join(c for c in number if c.isdigit() or c == "+")


def blocked(path: Path, number: str) -> bool:
    if not path.is_file():
        return False
    n = normalize(number)
    return any(normalize(line) == n for line in path.read_text().splitlines() if line.strip())


def add(path: Path, number: str) -> None:
    if blocked(path, number):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(normalize(number) + "\n")
