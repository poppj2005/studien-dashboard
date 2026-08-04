"""Tests für CsvImportService: Parsing und Validierung von CSV-Importdateien."""

import shutil
import unittest
from pathlib import Path

from src.domain.enums import ModulStatus, Pruefungsart, PruefungsStatus
from src.domain.exceptions import CsvImportError
from src.services.csv_import_service import CsvImportService

_TEST_VERZEICHNIS = Path(__file__).parent / "_tmp_csv_import_test"

_GUELTIGE_ZEILE = (
    "1;Einführung in die Wirtschaftsinformatik;DLBWIEWI01;5;ABGESCHLOSSEN;"
    "Klausur Wirtschaftsinformatik;KLAUSUR;BESTANDEN;2024-05-10;100;73;2,7"
)
_HEADER = (
    "Semester;Modul;Kurs-ID;ECTS;Status;Prüfung;Prüfungsart;Prüfungsstatus;"
    "Frist/Datum;Maximalpunkte;Punkte;Note"
)


class CsvImportServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        _TEST_VERZEICHNIS.mkdir(exist_ok=True)
        self.service = CsvImportService()

    def tearDown(self) -> None:
        shutil.rmtree(_TEST_VERZEICHNIS, ignore_errors=True)

    def _schreibe_csv(self, inhalt: str) -> Path:
        pfad = _TEST_VERZEICHNIS / "import.csv"
        pfad.write_text(inhalt, encoding="utf-8")
        return pfad

    def test_laedt_gueltige_zeile_korrekt(self) -> None:
        pfad = self._schreibe_csv(f"{_HEADER}\n{_GUELTIGE_ZEILE}\n")
        zeilen = self.service.lade_zeilen(pfad)

        self.assertEqual(len(zeilen), 1)
        zeile = zeilen[0]
        self.assertEqual(zeile.semester_nummer, 1)
        self.assertEqual(zeile.modultitel, "Einführung in die Wirtschaftsinformatik")
        self.assertEqual(zeile.kurs_id, "DLBWIEWI01")
        self.assertEqual(zeile.ects, 5)
        self.assertEqual(zeile.modul_status, ModulStatus.ABGESCHLOSSEN)
        self.assertEqual(zeile.pruefungstitel, "Klausur Wirtschaftsinformatik")
        self.assertEqual(zeile.art, Pruefungsart.KLAUSUR)
        self.assertEqual(zeile.status, PruefungsStatus.BESTANDEN)
        self.assertEqual(zeile.relevantes_datum.isoformat(), "2024-05-10")
        self.assertEqual(zeile.max_punkte, 100.0)
        self.assertEqual(zeile.punkte, 73.0)
        self.assertEqual(zeile.note, 2.7)

    def test_fehlende_spalte_wirft_fehler_mit_spaltenname(self) -> None:
        pfad = self._schreibe_csv("Semester;Modul;ECTS\n1;Test;5\n")
        with self.assertRaises(CsvImportError) as kontext:
            self.service.lade_zeilen(pfad)
        self.assertIn("Kurs-ID", str(kontext.exception))

    def test_ungueltiger_status_wirft_fehler_mit_zeilennummer(self) -> None:
        schlechte_zeile = (
            "1;Test;X1;5;UNBEKANNT;Klausur;KLAUSUR;BESTANDEN;2024-05-10;100;73;2,7"
        )
        pfad = self._schreibe_csv(f"{_HEADER}\n{schlechte_zeile}\n")
        with self.assertRaises(CsvImportError) as kontext:
            self.service.lade_zeilen(pfad)
        self.assertIn("Zeile 2", str(kontext.exception))
        self.assertIn("Status", str(kontext.exception))

    def test_note_ausserhalb_der_skala_wirft_fehler(self) -> None:
        schlechte_zeile = (
            "1;Test;X1;5;ABGESCHLOSSEN;Klausur;KLAUSUR;BESTANDEN;2024-05-10;100;73;9,9"
        )
        pfad = self._schreibe_csv(f"{_HEADER}\n{schlechte_zeile}\n")
        with self.assertRaises(CsvImportError) as kontext:
            self.service.lade_zeilen(pfad)
        self.assertIn("Note", str(kontext.exception))

    def test_leere_datei_ohne_datenzeilen_wirft_fehler(self) -> None:
        pfad = self._schreibe_csv(f"{_HEADER}\n")
        with self.assertRaises(CsvImportError):
            self.service.lade_zeilen(pfad)

    def test_fehlender_status_wird_aus_note_abgeleitet(self) -> None:
        zeile_ohne_status = (
            "1;Test;X1;5;ABGESCHLOSSEN;Klausur;KLAUSUR;;2024-05-10;100;73;2,7"
        )
        pfad = self._schreibe_csv(f"{_HEADER}\n{zeile_ohne_status}\n")
        zeilen = self.service.lade_zeilen(pfad)
        self.assertEqual(zeilen[0].status, PruefungsStatus.BESTANDEN)

    def test_leeres_datum_wird_zu_none(self) -> None:
        zeile_ohne_datum = "1;Test;X1;5;ABGESCHLOSSEN;Klausur;KLAUSUR;BESTANDEN;;100;73;2,7"
        pfad = self._schreibe_csv(f"{_HEADER}\n{zeile_ohne_datum}\n")
        zeilen = self.service.lade_zeilen(pfad)
        self.assertIsNone(zeilen[0].relevantes_datum)

    def test_fehlender_modultitel_bekommt_platzhalter_statt_fehler(self) -> None:
        zeile_ohne_modul = ";;X1;5;ABGESCHLOSSEN;;KLAUSUR;BESTANDEN;2024-05-10;100;73;2,7"
        pfad = self._schreibe_csv(f"{_HEADER}\n{zeile_ohne_modul}\n")
        zeilen = self.service.lade_zeilen(pfad)
        self.assertEqual(zeilen[0].modultitel, "Unbenanntes Modul (Zeile 2)")
        self.assertEqual(zeilen[0].pruefungstitel, "Unbenannte Prüfung (Zeile 2)")

    def test_fehlende_zahlen_und_enums_bekommen_standardwerte(self) -> None:
        # Semester, ECTS, Status und Prüfungsart sind leer.
        zeile_ohne_werte = ";Test;X1;;;Klausur;;BESTANDEN;2024-05-10;100;73;2,7"
        pfad = self._schreibe_csv(f"{_HEADER}\n{zeile_ohne_werte}\n")
        zeilen = self.service.lade_zeilen(pfad)
        zeile = zeilen[0]
        self.assertEqual(zeile.semester_nummer, 1)
        self.assertEqual(zeile.ects, 5)
        self.assertEqual(zeile.modul_status, ModulStatus.GEPLANT)
        self.assertEqual(zeile.art, Pruefungsart.KLAUSUR)

    def test_ungueltiger_wert_wird_trotz_leniency_weiterhin_abgelehnt(self) -> None:
        # Status ist nicht leer, sondern ein Tippfehler – muss weiterhin einen
        # Fehler auslösen statt stillschweigend einen Standardwert einzusetzen.
        schlechte_zeile = "1;Test;X1;5;FALSCH;Klausur;KLAUSUR;BESTANDEN;2024-05-10;100;73;2,7"
        pfad = self._schreibe_csv(f"{_HEADER}\n{schlechte_zeile}\n")
        with self.assertRaises(CsvImportError):
            self.service.lade_zeilen(pfad)


if __name__ == "__main__":
    unittest.main()
