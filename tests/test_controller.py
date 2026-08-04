"""Tests für DashboardController.aktualisiere_pruefung."""

import shutil
import unittest
from pathlib import Path

from src.controller.dashboard_controller import DashboardController
from src.domain.enums import ModulStatus, Pruefungsart, PruefungsStatus
from src.domain.exceptions import (
    CsvImportError,
    ModulBereitsVorhandenError,
    ModulNichtGefundenError,
    PruefungsleistungNichtGefundenError,
    SemesterNichtGefundenError,
)
from src.dto.eingabe_dtos import ModulAnlageDTO, PruefungsUpdateDTO
from src.repository.json_repository import JsonStudentRepository
from src.services.csv_import_service import CsvImportService
from src.services.dashboard_service import DashboardService
from src.services.fortschritts_service import FortschrittsService
from src.services.fristen_service import FristenService
from src.services.noten_service import NotenService
from tests.testdaten import erstelle_beispiel_student

_TEST_VERZEICHNIS = Path(__file__).parent / "_tmp_controller_test"


class DashboardControllerTest(unittest.TestCase):
    def setUp(self) -> None:
        _TEST_VERZEICHNIS.mkdir(exist_ok=True)
        datei_pfad = _TEST_VERZEICHNIS / "student.json"
        repository = JsonStudentRepository(datei_pfad)
        repository.speichere(erstelle_beispiel_student())

        dashboard_service = DashboardService(
            FortschrittsService(), NotenService(), FristenService()
        )
        self.controller = DashboardController(repository, dashboard_service, CsvImportService())

    def tearDown(self) -> None:
        shutil.rmtree(_TEST_VERZEICHNIS, ignore_errors=True)

    def test_aktualisiere_pruefung_setzt_note_und_status(self) -> None:
        update = PruefungsUpdateDTO(
            modultitel="Modul B",
            pruefungstitel="Klausur B",
            status=PruefungsStatus.BESTANDEN,
            note=1.7,
        )
        daten = self.controller.aktualisiere_pruefung(update)
        # Beide Module zählen jetzt als abgeschlossen/bestanden: 5 + 10 = 15 ECTS.
        self.assertEqual(daten.ects_ist, 15)

    def test_aktualisiere_pruefung_mit_note_ohne_status_leitet_bestanden_ab(self) -> None:
        # Nur eine Note eingetragen, kein Status gewählt: soll trotzdem als
        # bestanden zählen, sonst aktualisieren sich die ECTS nicht.
        update = PruefungsUpdateDTO(
            modultitel="Modul B",
            pruefungstitel="Klausur B",
            note=1.7,
        )
        daten = self.controller.aktualisiere_pruefung(update)
        self.assertEqual(daten.ects_ist, 15)

    def test_aktualisiere_pruefung_mit_nicht_bestehender_note_ohne_status(self) -> None:
        update = PruefungsUpdateDTO(
            modultitel="Modul B",
            pruefungstitel="Klausur B",
            note=4.7,
        )
        self.controller.aktualisiere_pruefung(update)

        student = self.controller._student
        modul_b = next(
            m
            for semester in student.studiengang.semester
            for m in semester.module
            if m.titel == "Modul B"
        )
        pruefung = next(p for p in modul_b.pruefungsleistungen if p.titel == "Klausur B")
        self.assertEqual(pruefung.status, PruefungsStatus.NICHT_BESTANDEN)

    def test_aktualisiere_pruefung_mit_unbekanntem_modul_wirft_fehler(self) -> None:
        update = PruefungsUpdateDTO(modultitel="unbekannt", pruefungstitel="x")
        with self.assertRaises(ModulNichtGefundenError):
            self.controller.aktualisiere_pruefung(update)

    def test_aktualisiere_pruefung_mit_unbekanntem_titel_wirft_fehler(self) -> None:
        update = PruefungsUpdateDTO(modultitel="Modul A", pruefungstitel="unbekannt")
        with self.assertRaises(PruefungsleistungNichtGefundenError):
            self.controller.aktualisiere_pruefung(update)

    def test_aktualisiere_pruefung_legt_neue_pruefungsleistung_im_bestehenden_modul_an(
        self,
    ) -> None:
        update = PruefungsUpdateDTO(
            modultitel="Modul B",
            pruefungstitel="Referat B",
            art=Pruefungsart.PORTFOLIO,
            status=PruefungsStatus.OFFEN,
        )
        self.controller.aktualisiere_pruefung(update)

        student = self.controller._student
        modul_b = next(
            m
            for semester in student.studiengang.semester
            for m in semester.module
            if m.titel == "Modul B"
        )
        titel = {p.titel for p in modul_b.pruefungsleistungen}
        self.assertIn("Referat B", titel)

    def test_aktualisiere_pruefung_legt_neues_modul_mit_pruefung_an(self) -> None:
        update = PruefungsUpdateDTO(
            modultitel="Modul C",
            pruefungstitel="Klausur C",
            art=Pruefungsart.KLAUSUR,
            ects=5,
            semester_nummer=2,
        )
        self.controller.aktualisiere_pruefung(update)

        student = self.controller._student
        neues_semester = next(
            s for s in student.studiengang.semester if s.nummer == 2
        )
        neues_modul = next(m for m in neues_semester.module if m.titel == "Modul C")
        self.assertEqual(neues_modul.titel, "Modul C")
        self.assertEqual(neues_modul.ects, 5)
        self.assertEqual(neues_modul.pruefungsleistungen[0].titel, "Klausur C")

    def test_aktualisiere_pruefung_setzt_modulstatus_haendisch(self) -> None:
        update = PruefungsUpdateDTO(
            modultitel="Modul B",
            pruefungstitel="Klausur B",
            modul_status=ModulStatus.ABGESCHLOSSEN,
        )
        self.controller.aktualisiere_pruefung(update)

        student = self.controller._student
        modul_b = next(
            m
            for semester in student.studiengang.semester
            for m in semester.module
            if m.titel == "Modul B"
        )
        self.assertEqual(modul_b.status, ModulStatus.ABGESCHLOSSEN)

    def test_lege_modul_an_erstellt_modul_ohne_pruefungsleistung(self) -> None:
        eingabe = ModulAnlageDTO(titel="Modul D", ects=5, semester_nummer=3)
        self.controller.lege_modul_an(eingabe)

        student = self.controller._student
        neues_semester = next(s for s in student.studiengang.semester if s.nummer == 3)
        neues_modul = next(m for m in neues_semester.module if m.titel == "Modul D")
        self.assertEqual(neues_modul.pruefungsleistungen, [])
        self.assertEqual(neues_modul.ects, 5)

    def test_lege_modul_an_ohne_semester_wirft_fehler(self) -> None:
        eingabe = ModulAnlageDTO(titel="Modul E", ects=5)
        with self.assertRaises(ModulNichtGefundenError):
            self.controller.lege_modul_an(eingabe)

    def test_lege_modul_an_mit_bestehendem_titel_bearbeitet_ects_und_status(self) -> None:
        eingabe = ModulAnlageDTO(
            titel="Modul B", ects=15, status=ModulStatus.ABGESCHLOSSEN
        )
        self.controller.lege_modul_an(eingabe)

        student = self.controller._student
        module_b = [
            m
            for semester in student.studiengang.semester
            for m in semester.module
            if m.titel == "Modul B"
        ]
        self.assertEqual(len(module_b), 1)
        self.assertEqual(module_b[0].status, ModulStatus.ABGESCHLOSSEN)
        self.assertEqual(module_b[0].ects, 15)

    def test_lege_modul_an_benennt_modul_um(self) -> None:
        eingabe = ModulAnlageDTO(titel="Modul B", ects=10, neuer_titel="Modul B neu")
        self.controller.lege_modul_an(eingabe)

        student = self.controller._student
        titel = {m.titel for s in student.studiengang.semester for m in s.module}
        self.assertIn("Modul B neu", titel)
        self.assertNotIn("Modul B", titel)

    def test_lege_modul_an_umbenennen_auf_bestehenden_titel_wirft_fehler(self) -> None:
        eingabe = ModulAnlageDTO(titel="Modul B", ects=10, neuer_titel="Modul A")
        with self.assertRaises(ModulBereitsVorhandenError):
            self.controller.lege_modul_an(eingabe)

    def test_loesche_modul_entfernt_modul_und_pruefungsleistungen(self) -> None:
        daten = self.controller.loesche_modul("Modul B")
        student = self.controller._student
        titel = {m.titel for s in student.studiengang.semester for m in s.module}
        self.assertNotIn("Modul B", titel)
        self.assertEqual(daten.ects_ist, 5)

    def test_loesche_modul_unbekannt_wirft_fehler(self) -> None:
        with self.assertRaises(ModulNichtGefundenError):
            self.controller.loesche_modul("unbekannt")

    def test_loesche_pruefungsleistung_entfernt_sie(self) -> None:
        self.controller.loesche_pruefungsleistung("Modul B", "Klausur B")
        student = self.controller._student
        modul_b = next(
            m
            for semester in student.studiengang.semester
            for m in semester.module
            if m.titel == "Modul B"
        )
        self.assertEqual(modul_b.pruefungsleistungen, [])

    def test_loesche_pruefungsleistung_unbekannt_wirft_fehler(self) -> None:
        with self.assertRaises(PruefungsleistungNichtGefundenError):
            self.controller.loesche_pruefungsleistung("Modul B", "unbekannt")

    def test_loesche_semester_entfernt_semester_und_module(self) -> None:
        daten = self.controller.loesche_semester(1)
        student = self.controller._student
        self.assertEqual(student.studiengang.semester, [])
        self.assertEqual(daten.ects_ist, 0)

    def test_loesche_semester_unbekannt_wirft_fehler(self) -> None:
        with self.assertRaises(SemesterNichtGefundenError):
            self.controller.loesche_semester(99)

    def test_aktualisiere_pruefung_speichert_punkte(self) -> None:
        update = PruefungsUpdateDTO(
            modultitel="Modul B", pruefungstitel="Klausur B", punkte=48.5
        )
        self.controller.aktualisiere_pruefung(update)

        student = self.controller._student
        modul_b = next(
            m
            for semester in student.studiengang.semester
            for m in semester.module
            if m.titel == "Modul B"
        )
        pruefung = next(p for p in modul_b.pruefungsleistungen if p.titel == "Klausur B")
        self.assertEqual(pruefung.punkte, 48.5)

    def test_setze_dashboard_zurueck_entfernt_alle_daten_aber_nicht_die_ziele(self) -> None:
        daten = self.controller.setze_dashboard_zurueck()

        self.assertEqual(daten.ects_ist, 0)
        self.assertEqual(daten.module, [])
        student = self.controller._student
        self.assertEqual(student.studiengang.semester, [])
        self.assertEqual(student.ects_ziel.ziel_ects, 15)

    def test_importiere_csv_legt_neues_modul_mit_pruefung_an(self) -> None:
        csv_pfad = _TEST_VERZEICHNIS / "import.csv"
        csv_pfad.write_text(
            "Semester;Modul;Kurs-ID;ECTS;Status;Prüfung;Prüfungsart;Prüfungsstatus;"
            "Frist/Datum;Maximalpunkte;Punkte;Note\n"
            "2;Neues CSV-Modul;X01;7;ABGESCHLOSSEN;CSV-Klausur;KLAUSUR;BESTANDEN;"
            "2026-01-15;100;90;1,3\n",
            encoding="utf-8",
        )

        daten = self.controller.importiere_csv(csv_pfad)

        student = self.controller._student
        neues_modul = next(
            m
            for s in student.studiengang.semester
            for m in s.module
            if m.titel == "Neues CSV-Modul"
        )
        self.assertEqual(neues_modul.ects, 7)
        self.assertEqual(neues_modul.kurs_id, "X01")
        pruefung = neues_modul.pruefungsleistungen[0]
        self.assertEqual(pruefung.note, 1.3)
        self.assertEqual(pruefung.punkte, 90.0)
        self.assertEqual(pruefung.max_punkte, 100.0)
        # Modul A (5) + Modul B (10, noch nicht bestanden) + neues Modul (7) = 12 ECTS.
        self.assertEqual(daten.ects_ist, 12)

    def test_importiere_csv_aktualisiert_bestehendes_modul_ueber_titel(self) -> None:
        csv_pfad = _TEST_VERZEICHNIS / "import.csv"
        csv_pfad.write_text(
            "Semester;Modul;Kurs-ID;ECTS;Status;Prüfung;Prüfungsart;Prüfungsstatus;"
            "Frist/Datum;Maximalpunkte;Punkte;Note\n"
            "1;Modul A;A01;20;AKTIV;Klausur A;KLAUSUR;BESTANDEN;2025-10-01;100;95;1,3\n",
            encoding="utf-8",
        )

        self.controller.importiere_csv(csv_pfad)

        student = self.controller._student
        module_a = [
            m
            for s in student.studiengang.semester
            for m in s.module
            if m.titel == "Modul A"
        ]
        self.assertEqual(len(module_a), 1)
        self.assertEqual(module_a[0].ects, 20)
        self.assertEqual(len(module_a[0].pruefungsleistungen), 1)

    def test_importiere_csv_mit_ungueltiger_datei_wirft_fehler_und_aendert_nichts(self) -> None:
        csv_pfad = _TEST_VERZEICHNIS / "import.csv"
        csv_pfad.write_text("Semester;Modul;ECTS\n1;Test;5\n", encoding="utf-8")

        with self.assertRaises(CsvImportError):
            self.controller.importiere_csv(csv_pfad)

        student = self.controller._student
        titel = {m.titel for s in student.studiengang.semester for m in s.module}
        self.assertEqual(titel, {"Modul A", "Modul B"})


if __name__ == "__main__":
    unittest.main()
