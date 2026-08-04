
"""Service zur Aggregation aller dashboard-relevanten Daten."""

from __future__ import annotations

from datetime import date

from src.domain.modelle import Student
from src.dto.ausgabe_dtos import DashboardDatenDTO, ModulUebersichtDTO, ZielAmpelDTO
from src.services.fortschritts_service import FortschrittsService
from src.services.fristen_service import FristenService
from src.services.noten_service import NotenService


class DashboardService:
    """Baut aus dem Studenten das vollständige, für die View bestimmte DTO."""

    def __init__(
        self,
        fortschritts_service: FortschrittsService,
        noten_service: NotenService,
        fristen_service: FristenService,
    ) -> None:
        self._fortschritts_service = fortschritts_service
        self._noten_service = noten_service
        self._fristen_service = fristen_service

    def erstelle_dashboard(
        self, student: Student, heute: date | None = None
    ) -> DashboardDatenDTO:
        """Aggregiert Fortschritts-, Noten- und Fristendaten zu einem DashboardDatenDTO.

        heute ist injizierbar, damit Fristen-Bewertungen in Tests deterministisch bleiben;
        im Produktivbetrieb übergibt DashboardApp keinen Wert, sodass date.today() greift.
        """
        heute = heute if heute is not None else date.today()

        naechste_pruefung = self._fristen_service.ermittle_naechsten_termin(student)
        module_uebersicht = [
            ModulUebersichtDTO(semester_nummer=semester.nummer, modul=modul)
            for semester in student.studiengang.semester
            for modul in semester.module
        ]

        return DashboardDatenDTO(
            student_name=student.name,
            studiengang_name=student.studiengang.name,
            ects_ist=self._fortschritts_service.berechne_ects_ist(student),
            ects_ziel=self._fortschritts_service.ermittle_ects_ziel(student),
            ects_fortschritt_prozent=self._fortschritts_service.berechne_fortschritt_prozent(
                student
            ),
            notenschnitt=self._noten_service.berechne_notenschnitt(student),
            offene_pruefungen=self._fristen_service.zaehle_offene_pruefungen(student),
            angemeldete_pruefungen=self._fristen_service.zaehle_angemeldete_pruefungen(student),
            fristen_risiko_anzahl=self._fristen_service.zaehle_risiko_pruefungen(student, heute),
            naechster_termin=naechste_pruefung.relevantes_datum if naechste_pruefung else None,
            naechste_pruefung_titel=naechste_pruefung.titel if naechste_pruefung else None,
            zielampeln=ZielAmpelDTO(
                ects=self._fortschritts_service.bewerte_ects_ziel(student),
                noten=self._noten_service.bewerte_notenziel(student),
                fristen=self._fristen_service.bewerte_fristenziel(student, heute),
            ),
            module=module_uebersicht,
        )
