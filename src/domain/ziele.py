"""Studienziele: abstrakte Basis sowie konkrete ECTS-, Noten- und Fristenziele.

ziel_ects wird ausschließlich in EctsZiel gehalten (keine doppelte Ablage
am Studiengang), damit es nur eine verbindliche Quelle für den ECTS-Zielwert gibt.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass
class Studienziel(ABC):
    """Gemeinsame Basis aller Studienziele."""

    bezeichnung: str

    @abstractmethod
    def kurzbeschreibung(self) -> str:
        """Liefert eine kurze, für die GUI geeignete Beschreibung des Ziels."""


@dataclass
class EctsZiel(Studienziel):
    """Einzige Quelle für das angestrebte ECTS-Ziel des Studiengangs."""

    ziel_ects: int
    ziel_datum: date | None = None

    def kurzbeschreibung(self) -> str:
        """Gibt eine kurze, GUI-freundliche Beschreibung des ECTS-Ziels zurück."""
        return f"Ziel: {self.ziel_ects} ECTS"


@dataclass
class NotenZiel(Studienziel):
    """Angestrebter maximaler Notendurchschnitt."""

    ziel_notenschnitt: float

    def kurzbeschreibung(self) -> str:
        """Gibt eine kurze, GUI-freundliche Beschreibung des Notenziels zurück."""
        return f"Zielwert: max. {self.ziel_notenschnitt:.1f}"


@dataclass
class FristenZiel(Studienziel):
    """Schwellenwert (in Tagen), ab dem eine offene Prüfung als terminkritisch gilt."""

    warnschwelle_tage: int = 14

    def kurzbeschreibung(self) -> str:
        """Gibt eine kurze, GUI-freundliche Beschreibung des Fristenziels zurück."""
        return f"Risiko ab < {self.warnschwelle_tage} Tagen"
