"""Tests für den NotenService."""

import unittest

from src.domain.enums import AmpelStatus
from src.services.noten_service import NotenService
from tests.testdaten import erstelle_beispiel_student


class NotenServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = NotenService()
        self.student = erstelle_beispiel_student()

    def test_berechne_notenschnitt_beruecksichtigt_nur_bewertete_leistungen(self) -> None:
        # Nur Klausur A hat eine Note (2.0); Klausur B ist noch unbewertet.
        self.assertEqual(self.service.berechne_notenschnitt(self.student), 2.0)

    def test_bewerte_notenziel_innerhalb_des_ziels_ist_gruen(self) -> None:
        self.assertEqual(self.service.bewerte_notenziel(self.student), AmpelStatus.GRUEN)

    def test_notenschnitt_ohne_bewertete_leistungen_ist_none(self) -> None:
        for semester in self.student.studiengang.semester:
            for modul in semester.module:
                for pruefungsleistung in modul.pruefungsleistungen:
                    pruefungsleistung.note = None
        self.assertIsNone(self.service.berechne_notenschnitt(self.student))


if __name__ == "__main__":
    unittest.main()
