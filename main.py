"""Einstiegspunkt des Studien-Dashboard-Prototyps.

Start über: python main.py
"""

from __future__ import annotations

from pathlib import Path

from src.app import DashboardApp

DATEN_DATEI = Path(__file__).parent / "data" / "student.json"


def main() -> None:
    app = DashboardApp(DATEN_DATEI)
    app.run()


if __name__ == "__main__":
    main()
