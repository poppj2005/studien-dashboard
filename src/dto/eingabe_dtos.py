"""Eingabe-DTOs: strukturierte Übergabeobjekte von der View zum Controller."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.domain.enums import ModulStatus, Pruefungsart, PruefungsStatus


@dataclass
class PruefungsUpdateDTO:
    """Typisierte Eingabe zur Aktualisierung – oder Neuanlage – einer Prüfungsleistung.

    modultitel und pruefungstitel identifizieren die Prüfungsleistung: der
    Modultitel ist der einzige Schlüssel eines Moduls, es gibt keine
    zusätzliche Modulnummer. Existieren Modul bzw. Prüfungsleistung bereits,
    werden nur die gesetzten übrigen Felder übernommen. Existiert das Modul
    nicht, legt der Controller es unter modultitel neu an – dafür werden
    zusätzlich ects und semester_nummer benötigt (für eine neue
    Prüfungsleistung: art).
    """

    modultitel: str
    pruefungstitel: str
    status: PruefungsStatus | None = None
    note: float | None = None
    punkte: float | None = None
    relevantes_datum: date | None = None
    art: Pruefungsart | None = None
    modul_status: ModulStatus | None = None
    ects: int | None = None
    semester_nummer: int | None = None


@dataclass
class ModulAnlageDTO:
    """Typisierte Eingabe, um ein Modul direkt anzulegen oder zu bearbeiten – ganz
    ohne Prüfungsleistung.

    titel wird von Hand eingegeben und identifiziert das Modul. Existiert
    bereits ein Modul mit diesem Titel, werden ects/status/neuer_titel
    übernommen (Bearbeiten) statt ein zweites Modul anzulegen. Für ein neues
    Modul werden ects und semester_nummer benötigt.
    """

    titel: str
    ects: int
    semester_nummer: int | None = None
    status: ModulStatus | None = None
    neuer_titel: str | None = None
