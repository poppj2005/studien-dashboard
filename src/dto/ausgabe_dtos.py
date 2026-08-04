"""Ausgabe-DTOs: typisierte Datenstrukturen von Service/Controller zur View.

Optionale Werte sind explizit als `| None` markiert, damit fehlende Daten
(z. B. noch keine Note oder kein anstehender Termin) nicht durch
Platzhalter verschleiert werden.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.domain.enums import AmpelStatus
from src.domain.modelle import Modul


@dataclass
class ZielAmpelDTO:
    """Typisierte Ampelbewertung der drei Studienziele – kein generisches dict."""

    ects: AmpelStatus
    noten: AmpelStatus
    fristen: AmpelStatus


@dataclass
class ModulUebersichtDTO:
    """Ein Modul zusammen mit seiner Semesterzuordnung, für die Tabellenanzeige.

    Die Semesterzuordnung wird beim Aufbau des Dashboards aus der
    Semester-Gruppierung abgeleitet, nicht zusätzlich am Modul gespeichert –
    sonst könnte sie mit Studiengang.semester aus dem Tritt geraten.
    """

    semester_nummer: int
    modul: Modul


@dataclass
class DashboardDatenDTO:
    """Gesamtansicht aller für das Dashboard relevanten, aggregierten Daten."""

    student_name: str
    studiengang_name: str
    ects_ist: int
    ects_ziel: int
    ects_fortschritt_prozent: float
    notenschnitt: float | None
    offene_pruefungen: int
    angemeldete_pruefungen: int
    fristen_risiko_anzahl: int
    naechster_termin: date | None
    naechste_pruefung_titel: str | None
    zielampeln: ZielAmpelDTO
    module: list[ModulUebersichtDTO]
