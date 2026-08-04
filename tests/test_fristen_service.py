"""Tests für den FristenService."""

import unittest
from datetime import date

from src.domain.enums import AmpelStatus
from src.services.fristen_service import FristenService
from tests.testdaten import erstelle_beispiel_student


class FristenServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = FristenService()
        self.student = erstelle_beispiel_student()

    def test_zaehle_offene_pruefungen(self) -> None:
        # Klausur A ist bestanden, nur Klausur B (angemeldet) zählt als offen.
        self.assertEqual(self.service.zaehle_offene_pruefungen(self.student), 1)

    def test_zaehle_angemeldete_pruefungen(self) -> None:
        self.assertEqual(self.service.zaehle_angemeldete_pruefungen(self.student), 1)

    def test_ermittle_naechsten_termin(self) -> None:
        naechste = self.service.ermittle_naechsten_termin(self.student)
        self.assertIsNotNone(naechste)
        self.assertEqual(naechste.titel, "Klausur B")

    def test_zaehle_risiko_pruefungen_innerhalb_der_warnschwelle(self) -> None:
        heute = date(2026, 1, 10)  # 10 Tage vor Klausur B, unter der Warnschwelle von 14 Tagen
        self.assertEqual(self.service.zaehle_risiko_pruefungen(self.student, heute), 1)

    def test_zaehle_risiko_pruefungen_ausserhalb_der_warnschwelle(self) -> None:
        heute = date(2025, 12, 1)  # weit vor Klausur B
        self.assertEqual(self.service.zaehle_risiko_pruefungen(self.student, heute), 0)

    def test_bewerte_fristenziel_innerhalb_der_warnschwelle_ist_rot(self) -> None:
        heute = date(2026, 1, 10)
        self.assertEqual(self.service.bewerte_fristenziel(self.student, heute), AmpelStatus.ROT)


if __name__ == "__main__":
    unittest.main()
