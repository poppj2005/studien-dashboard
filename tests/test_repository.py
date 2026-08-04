"""Tests für JsonStudentRepository: Laden und Speichern muss verlustfrei sein."""

import shutil
import unittest
from pathlib import Path

from src.repository.json_repository import JsonStudentRepository
from tests.testdaten import erstelle_beispiel_student

_TEST_VERZEICHNIS = Path(__file__).parent / "_tmp_repository_test"


class JsonStudentRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        _TEST_VERZEICHNIS.mkdir(exist_ok=True)
        self.datei_pfad = _TEST_VERZEICHNIS / "student.json"
        self.repository = JsonStudentRepository(self.datei_pfad)

    def tearDown(self) -> None:
        shutil.rmtree(_TEST_VERZEICHNIS, ignore_errors=True)

    def test_speichern_und_laden_liefert_gleichwertigen_studenten(self) -> None:
        student = erstelle_beispiel_student()
        self.repository.speichere(student)
        geladener_student = self.repository.lade_student()

        self.assertEqual(geladener_student.name, student.name)
        self.assertEqual(geladener_student.ects_ziel.ziel_ects, student.ects_ziel.ziel_ects)
        self.assertEqual(len(geladener_student.studiengang.semester), 1)

        modul = geladener_student.studiengang.semester[0].module[0]
        original_modul = student.studiengang.semester[0].module[0]
        self.assertEqual(modul.titel, original_modul.titel)
        self.assertEqual(modul.ects, original_modul.ects)
        self.assertEqual(modul.kurs_id, original_modul.kurs_id)
        self.assertEqual(modul.pruefungsleistungen[0].note, original_modul.pruefungsleistungen[0].note)
        self.assertEqual(
            modul.pruefungsleistungen[0].punkte, original_modul.pruefungsleistungen[0].punkte
        )
        self.assertEqual(
            modul.pruefungsleistungen[0].max_punkte,
            original_modul.pruefungsleistungen[0].max_punkte,
        )
        self.assertEqual(
            modul.pruefungsleistungen[0].relevantes_datum,
            original_modul.pruefungsleistungen[0].relevantes_datum,
        )

    def test_fehlende_datei_erzeugt_beispieldaten(self) -> None:
        self.assertFalse(self.datei_pfad.exists())
        student = self.repository.lade_student()
        self.assertTrue(self.datei_pfad.exists())
        self.assertTrue(student.name)
        self.assertGreater(len(student.studiengang.semester), 0)


if __name__ == "__main__":
    unittest.main()
