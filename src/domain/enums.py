"""Enumerationen des Studien-Dashboards.

Als str-Enums abgeleitet, damit sie sich verlustfrei in JSON
(de-)serialisieren lassen (Enum.value ist ein gewöhnlicher String).
"""

from enum import Enum


class ModulStatus(str, Enum):
    """Bearbeitungsstatus eines Moduls."""

    GEPLANT = "geplant"
    AKTIV = "aktiv"
    ABGESCHLOSSEN = "abgeschlossen"


class PruefungsStatus(str, Enum):
    """Bearbeitungsstatus einer Prüfungsleistung."""

    OFFEN = "offen"
    ANGEMELDET = "angemeldet"
    BESTANDEN = "bestanden"
    NICHT_BESTANDEN = "nicht_bestanden"


class Pruefungsart(str, Enum):
    """Art der Prüfungsleistung."""

    KLAUSUR = "klausur"
    HAUSARBEIT = "hausarbeit"
    PROJEKT = "projekt"
    PORTFOLIO = "portfolio"


class AmpelStatus(str, Enum):
    """Ampelfarbe zur Bewertung eines Studienziels."""

    GRUEN = "gruen"
    GELB = "gelb"
    ROT = "rot"
