"""Tests für den FortschrittsService."""

import unittest

from src.domain.enums import AmpelStatus
from src.services.fortschritts_service import FortschrittsService
from tests.testdaten import erstelle_beispiel_student


class FortschrittsServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = FortschrittsService()
        self.student = erstelle_beispiel_student()

    def test_berechne_ects_ist_zaehlt_nur_abgeschlossene_oder_bestandene_module(self) -> None:
        # Nur Modul A (abgeschlossen, 5 ECTS) zählt; Modul B ist nur angemeldet.
        self.assertEqual(self.service.berechne_ects_ist(self.student), 5)

    def test_berechne_fortschritt_prozent(self) -> None:
        fortschritt = self.service.berechne_fortschritt_prozent(self.student)
        self.assertAlmostEqual(fortschritt, (5 / 15) * 100, places=1)

    def test_bewerte_ects_ziel_bei_niedrigem_fortschritt_ist_rot(self) -> None:
        self.assertEqual(self.service.bewerte_ects_ziel(self.student), AmpelStatus.ROT)

    def test_fortschritt_bei_ziel_null_ist_null(self) -> None:
        self.student.ects_ziel.ziel_ects = 0
        self.assertEqual(self.service.berechne_fortschritt_prozent(self.student), 0.0)


if __name__ == "__main__":
    unittest.main()
