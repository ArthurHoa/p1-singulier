"""
Modele utilisateurs/badges.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv


@dataclass
class Badge:
    """Badge associe a un utilisateur."""

    code: str
    name: str | None


def read_badges(csv_path: str | Path) -> list[Badge]:
    """Lit badges.csv et retourne la liste des badges.

    Le CSV attend 3 colonnes avec un header: Numero, ID, Nom.
    """
    path = Path(csv_path)
    badges: list[Badge] = []

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            code = (row.get("ID") or "").strip()
            name = (row.get("Nom") or "").strip()
            if not code:
                continue
            badges.append(Badge(code=code, name=name or None))

    return badges


class Badgelist:
    """Conteneur de badges chargee depuis un CSV."""

    def __init__(self):
        base_dir = Path(__file__).resolve().parents[2]
        badges_path = base_dir / "badges" / "badges.csv"
        self.badges = read_badges(badges_path)

    def print_badges(self):
        for badge in self.badges:
            print(f"{badge.code} - {badge.name}")
