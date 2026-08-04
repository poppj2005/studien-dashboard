"""Domänenmodelle des Studien-Dashboards (fachliche Kernobjekte).

Abbildung: Student -> Studiengang -> Semester -> Modul -> Pruefungsleistung.
Abgeleitete Zustände (z. B. ob eine Prüfungsleistung bewertet ist) werden
nicht gespeichert, sondern als Property berechnet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from src.domain.enums import ModulStatus, Pruefungsart, PruefungsStatus
from src.domain.ziele import EctsZiel, FristenZiel, NotenZiel

ECTS_VORSCHLAG = 5
"""Vorbelegter ECTS-Vorschlag fürs Anlegeformular – Modul.ects bleibt frei editierbar."""

NOTE_BESTEHENSGRENZE = 4.0
"""Deutsches Notensystem: Noten bis einschließlich dieses Werts gelten als bestanden."""

NOTE_MIN = 1.0
NOTE_MAX = 5.0
"""Deutsches Notensystem: gültiger Wertebereich einer Note (1,0 = beste, 5,0 = schlechteste)."""


@dataclass
class Pruefungsleistung:
    """Eine einzelne Prüfungs- oder Abgabeleistung innerhalb eines Moduls.

    punkte ist ein rein informatives Rohpunkte-Feld (z. B. 42 von 60 Punkten)
    unabhängig von der daraus resultierenden Note.
    """

    titel: str
    art: Pruefungsart
    status: PruefungsStatus = PruefungsStatus.OFFEN
    note: float | None = None
    punkte: float | None = None
    max_punkte: float | None = None
    relevantes_datum: date | None = None

    @property
    def ist_bewertet(self) -> bool:
        """Abgeleiteter Bewertungsstatus – kein eigenes gespeichertes Feld."""
        return self.note is not None or self.status in (
            PruefungsStatus.BESTANDEN,
            PruefungsStatus.NICHT_BESTANDEN,
        )


@dataclass
class Modul:
    """Ein Modul des Studiengangs mit seinen Prüfungsleistungen.

    Der Modultitel ist zugleich der fachliche Schlüssel, über den Module
    gesucht und gepflegt werden – es gibt keine zusätzliche Modulnummer.
    kurs_id ist ein rein informatives Feld (z. B. aus einem CSV-Import) und
    wird nirgends zum Nachschlagen verwendet.
    """

    titel: str
    ects: int
    status: ModulStatus = ModulStatus.GEPLANT
    kurs_id: str | None = None
    pruefungsleistungen: list[Pruefungsleistung] = field(default_factory=list)


@dataclass
class Semester:
    """Ein Fachsemester mit den darin belegten Modulen."""

    nummer: int
    module: list[Modul] = field(default_factory=list)


@dataclass
class Studiengang:
    """Der gesamte Studiengang, gegliedert in Semester."""

    name: str
    semester: list[Semester] = field(default_factory=list)


@dataclass
class Student:
    """Die Studentin/der Student mit Studiengang und den drei Studienzielen.

    Die Studienziele werden bewusst als eigene, typisierte Felder gehalten
    (statt als generische Liste von Studienziel), damit die Services ohne
    Typprüfung direkt auf ects_ziel/noten_ziel/fristen_ziel zugreifen können.
    """

    name: str
    studiengang: Studiengang
    ects_ziel: EctsZiel
    noten_ziel: NotenZiel
    fristen_ziel: FristenZiel
