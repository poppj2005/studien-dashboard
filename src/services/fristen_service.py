"""Service zur Auswertung offener Prüfungsleistungen und relevanter Termine."""

from __future__ import annotations

from datetime import date

from src.domain.enums import AmpelStatus, PruefungsStatus
from src.domain.modelle import Pruefungsleistung, Student

_OFFENE_STATI = (PruefungsStatus.OFFEN, PruefungsStatus.ANGEMELDET)


class FristenService:
    """Zählt offene Prüfungsleistungen und bewertet deren zeitliche Dringlichkeit."""

    def zaehle_offene_pruefungen(self, student: Student) -> int:
        """Zählt alle offenen Prüfungsleistungen des Studenten."""
        return len(self._offene_pruefungsleistungen(student))

    def zaehle_angemeldete_pruefungen(self, student: Student) -> int:
        """Zählt nur die offenen Prüfungsleistungen mit dem Status 'angemeldet'."""
        return sum(
            1
            for pruefungsleistung in self._offene_pruefungsleistungen(student)
            if pruefungsleistung.status == PruefungsStatus.ANGEMELDET
        )

    def ermittle_naechsten_termin(self, student: Student) -> Pruefungsleistung | None:
        """Liefert die offene Prüfungsleistung mit dem nächstgelegenen relevanten Datum."""
        offene_mit_datum = [
            p for p in self._offene_pruefungsleistungen(student) if p.relevantes_datum is not None
        ]
        if not offene_mit_datum:
            return None
        return min(offene_mit_datum, key=lambda p: p.relevantes_datum)

    def zaehle_risiko_pruefungen(self, student: Student, heute: date) -> int:
        """Zählt offene Prüfungsleistungen, deren Termin überfällig ist oder
        innerhalb der Warnschwelle von fristen_ziel liegt."""
        warnschwelle_tage = student.fristen_ziel.warnschwelle_tage
        risiko_anzahl = 0
        for pruefungsleistung in self._offene_pruefungsleistungen(student):
            if pruefungsleistung.relevantes_datum is None:
                continue
            verbleibende_tage = (pruefungsleistung.relevantes_datum - heute).days
            if verbleibende_tage < warnschwelle_tage:
                risiko_anzahl += 1
        return risiko_anzahl

    def bewerte_fristenziel(self, student: Student, heute: date) -> AmpelStatus:
        """Bewertet die aktuelle Fristensituation und gibt den passenden Ampelstatus zurück."""
        if self.zaehle_risiko_pruefungen(student, heute) > 0:
            return AmpelStatus.ROT
        offene_mit_datum = any(
            p.relevantes_datum is not None for p in self._offene_pruefungsleistungen(student)
        )
        return AmpelStatus.GELB if offene_mit_datum else AmpelStatus.GRUEN

    @staticmethod
    def _offene_pruefungsleistungen(student: Student) -> list[Pruefungsleistung]:
        return [
            pruefungsleistung
            for semester in student.studiengang.semester
            for modul in semester.module
            for pruefungsleistung in modul.pruefungsleistungen
            if pruefungsleistung.status in _OFFENE_STATI
        ]
