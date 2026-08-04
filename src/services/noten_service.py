"""Service zur Berechnung des Notendurchschnitts."""

from __future__ import annotations

from src.domain.enums import AmpelStatus
from src.domain.modelle import Student


class NotenService:
    """Berechnet den ECTS-gewichteten Notendurchschnitt bewerteter Prüfungsleistungen."""

    def berechne_notenschnitt(self, student: Student) -> float | None:
        """Berücksichtigt jede Prüfungsleistung mit gesetzter Note (note != None)."""
        gewichtete_summe = 0.0
        gesamt_ects = 0
        for semester in student.studiengang.semester:
            for modul in semester.module:
                for pruefungsleistung in modul.pruefungsleistungen:
                    if pruefungsleistung.note is None:
                        continue
                    gewichtete_summe += pruefungsleistung.note * modul.ects
                    gesamt_ects += modul.ects

        if gesamt_ects == 0:
            return None
        return round(gewichtete_summe / gesamt_ects, 2)

    def bewerte_notenziel(self, student: Student) -> AmpelStatus:
        """Solange keine Note vorliegt, besteht noch kein Handlungsbedarf (GRUEN)."""
        notenschnitt = self.berechne_notenschnitt(student)
        if notenschnitt is None:
            return AmpelStatus.GRUEN

        ziel_notenschnitt = student.noten_ziel.ziel_notenschnitt
        if notenschnitt <= ziel_notenschnitt:
            return AmpelStatus.GRUEN
        if notenschnitt <= ziel_notenschnitt + 0.5:
            return AmpelStatus.GELB
        return AmpelStatus.ROT
