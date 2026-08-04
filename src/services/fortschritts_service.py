"""Service zur Berechnung des ECTS-Fortschritts."""

from __future__ import annotations

from src.domain.enums import AmpelStatus, ModulStatus, PruefungsStatus
from src.domain.modelle import Modul, Student


class FortschrittsService:
    """Berechnet erreichte ECTS und bewertet den Fortschritt gegenüber dem EctsZiel."""

    def berechne_ects_ist(self, student: Student) -> int:
        """Summiert die ECTS aller Module, die abgeschlossen oder bestanden sind."""
        erreichte_ects = 0
        for semester in student.studiengang.semester:
            for modul in semester.module:
                if self._ist_modul_abgeschlossen(modul):
                    erreichte_ects += modul.ects
        return erreichte_ects

    def ermittle_ects_ziel(self, student: Student) -> int:
        """Liefert das im EctsZiel hinterlegte Zielwert (einzige Quelle für ziel_ects)."""
        return student.ects_ziel.ziel_ects

    def berechne_fortschritt_prozent(self, student: Student) -> float:
        """Fortschritt in Prozent relativ zum EctsZiel, gedeckelt bei 100 %."""
        ziel_ects = self.ermittle_ects_ziel(student)
        if ziel_ects <= 0:
            return 0.0
        ist_ects = self.berechne_ects_ist(student)
        return round(min(ist_ects / ziel_ects, 1.0) * 100, 1)

    def bewerte_ects_ziel(self, student: Student) -> AmpelStatus:
        """Bewertet das ECTS-Ziel anhand des erreichten Fortschritts und gibt einen Ampelstatus zurück."""
        fortschritt_prozent = self.berechne_fortschritt_prozent(student)
        if fortschritt_prozent >= 75:
            return AmpelStatus.GRUEN
        if fortschritt_prozent >= 40:
            return AmpelStatus.GELB
        return AmpelStatus.ROT

    @staticmethod
    def _ist_modul_abgeschlossen(modul: Modul) -> bool:
        if modul.status == ModulStatus.ABGESCHLOSSEN:
            return True
        return any(p.status == PruefungsStatus.BESTANDEN for p in modul.pruefungsleistungen)
