"""Startpunkt-Klasse: verdrahtet alle Schichten des Studien-Dashboards."""

from __future__ import annotations

from pathlib import Path

from src.controller.dashboard_controller import DashboardController
from src.repository.json_repository import JsonStudentRepository
from src.services.csv_import_service import CsvImportService
from src.services.dashboard_service import DashboardService
from src.services.fortschritts_service import FortschrittsService
from src.services.fristen_service import FristenService
from src.services.noten_service import NotenService
from src.view.tkinter_view import TkinterDashboardView


class DashboardApp:
    """Baut das Abhängigkeitsgeflecht der Schichten auf und startet die GUI."""

    def __init__(self, daten_datei: Path) -> None:
        repository = JsonStudentRepository(daten_datei)
        dashboard_service = DashboardService(
            FortschrittsService(), NotenService(), FristenService()
        )
        self._controller = DashboardController(
            repository, dashboard_service, CsvImportService()
        )

    def run(self) -> None:
        """Startet die Tkinter-Hauptschleife."""
        view = TkinterDashboardView(self._controller)
        view.mainloop()
