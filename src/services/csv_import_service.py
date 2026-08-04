"""Service zum Einlesen und Validieren von CSV-Importdateien.

Erwartet eine semikolon-getrennte CSV-Datei mit deutschem Dezimalkomma
(z. B. '2,7' als Note). Validiert vollständig, bevor irgendetwas übernommen
wird: entweder ist die ganze Datei gültig, oder es wird gar nichts importiert
– so landet der Studierendendatensatz nie in einem halb importierten Zustand.

Fehlt in einer Zeile eine Pflichtspalte (leere Zelle), wird eine geeignete
Standardbezeichnung eingesetzt (siehe _STANDARD_*) statt die Zeile abzulehnen.
Nur tatsächlich ungültige, nicht-leere Werte (z. B. Tippfehler bei einem
Status) führen zu einem Fehler.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TypeVar

from src.domain.enums import ModulStatus, Pruefungsart, PruefungsStatus
from src.domain.exceptions import CsvImportError
from src.domain.modelle import ECTS_VORSCHLAG, NOTE_BESTEHENSGRENZE, NOTE_MAX, NOTE_MIN

_STANDARD_SEMESTER = 1
_STANDARD_MODULSTATUS = ModulStatus.GEPLANT
_STANDARD_PRUEFUNGSART = Pruefungsart.KLAUSUR
"""Werte, die eingesetzt werden, wenn eine Pflichtspalte in einer Zeile leer ist,
statt den Import der ganzen Datei abzubrechen."""

_PFLICHTSPALTEN = (
    "Semester",
    "Modul",
    "Kurs-ID",
    "ECTS",
    "Status",
    "Prüfung",
    "Prüfungsart",
    "Prüfungsstatus",
    "Frist/Datum",
    "Maximalpunkte",
    "Punkte",
    "Note",
)

_MAX_ANGEZEIGTE_FEHLER = 15

_EnumTyp = TypeVar("_EnumTyp")


@dataclass
class CsvZeile:
    """Eine vollständig validierte und typisierte Zeile aus der CSV-Importdatei."""

    semester_nummer: int
    modultitel: str
    kurs_id: str | None
    ects: int
    modul_status: ModulStatus
    pruefungstitel: str
    art: Pruefungsart
    status: PruefungsStatus
    relevantes_datum: date | None
    max_punkte: float | None
    punkte: float | None
    note: float | None


class CsvImportService:
    """Liest eine CSV-Importdatei ein und liefert validierte, typisierte Zeilen."""

    def lade_zeilen(self, datei_pfad: Path) -> list[CsvZeile]:
        """Lädt die CSV-Datei ein, validiert sie und gibt typisierte Zeilen zurück."""
        with datei_pfad.open("r", encoding="utf-8-sig", newline="") as datei:
            reader = csv.DictReader(datei, delimiter=";")
            spalten = [spalte.strip() for spalte in (reader.fieldnames or [])]
            fehlende_spalten = [spalte for spalte in _PFLICHTSPALTEN if spalte not in spalten]
            if fehlende_spalten:
                raise CsvImportError(
                    "Die CSV-Datei hat folgende fehlende Spalten: "
                    f"{', '.join(fehlende_spalten)}.\n\n"
                    f"Erwartet werden (durch Semikolon getrennt): {', '.join(_PFLICHTSPALTEN)}."
                )

            fehler: list[str] = []
            zeilen: list[CsvZeile] = []
            for zeilennummer, rohdaten in enumerate(reader, start=2):
                try:
                    zeilen.append(self._zu_zeile(rohdaten, zeilennummer))
                except ValueError as fehlerursache:
                    fehler.append(f"Zeile {zeilennummer}: {fehlerursache}")

        if fehler:
            angezeigt = fehler[:_MAX_ANGEZEIGTE_FEHLER]
            text = "\n".join(angezeigt)
            if len(fehler) > _MAX_ANGEZEIGTE_FEHLER:
                text += f"\n… und {len(fehler) - _MAX_ANGEZEIGTE_FEHLER} weitere Fehler."
            raise CsvImportError(f"{len(fehler)} Zeile(n) mit ungültigen Werten:\n\n{text}")

        if not zeilen:
            raise CsvImportError("Die CSV-Datei enthält keine Datenzeilen.")

        return zeilen

    def _zu_zeile(self, rohdaten: dict, zeilennummer: int) -> CsvZeile:
        def wert(spalte: str) -> str:
            return (rohdaten.get(spalte) or "").strip()

        # Fehlt eine Pflichtspalte in einer einzelnen Zeile (Zelle leer), wird eine
        # geeignete Standardbezeichnung eingesetzt statt den ganzen Import
        # abzulehnen. Ein vorhandener, aber ungültiger Wert (z. B. Tippfehler bei
        # einem Status) führt weiterhin zu einem Fehler – das ist kein Fehlen.
        modultitel = wert("Modul") or f"Unbenanntes Modul (Zeile {zeilennummer})"
        pruefungstitel = wert("Prüfung") or f"Unbenannte Prüfung (Zeile {zeilennummer})"

        semester_text = wert("Semester")
        semester_nummer = (
            self._zu_int(semester_text, "Semester") if semester_text else _STANDARD_SEMESTER
        )

        ects_text = wert("ECTS")
        if ects_text:
            ects = self._zu_int(ects_text, "ECTS")
            if ects <= 0:
                raise ValueError("Spalte 'ECTS' muss eine positive Ganzzahl sein.")
        else:
            ects = ECTS_VORSCHLAG

        status_text = wert("Status")
        modul_status = (
            self._zu_enum(ModulStatus, status_text, "Status")
            if status_text
            else _STANDARD_MODULSTATUS
        )

        art_text = wert("Prüfungsart")
        art = (
            self._zu_enum(Pruefungsart, art_text, "Prüfungsart")
            if art_text
            else _STANDARD_PRUEFUNGSART
        )

        note = self._zu_optionale_zahl(wert("Note"), "Note")
        if note is not None and not (NOTE_MIN <= note <= NOTE_MAX):
            raise ValueError(
                f"Spalte 'Note' muss zwischen {NOTE_MIN:.1f} und {NOTE_MAX:.1f} liegen."
            )

        punkte = self._zu_optionale_zahl(wert("Punkte"), "Punkte")
        if punkte is not None and punkte < 0:
            raise ValueError("Spalte 'Punkte' darf nicht negativ sein.")

        max_punkte = self._zu_optionale_zahl(wert("Maximalpunkte"), "Maximalpunkte")
        if max_punkte is not None and max_punkte < 0:
            raise ValueError("Spalte 'Maximalpunkte' darf nicht negativ sein.")

        pruefungsstatus_text = wert("Prüfungsstatus")
        if pruefungsstatus_text:
            pruefungsstatus = self._zu_enum(
                PruefungsStatus, pruefungsstatus_text, "Prüfungsstatus"
            )
        elif note is not None:
            # Kein Status angegeben, aber eine Note vorhanden: wie beim manuellen
            # Pflegen aus der Note ableiten, statt die Zeile abzulehnen.
            pruefungsstatus = (
                PruefungsStatus.BESTANDEN
                if note <= NOTE_BESTEHENSGRENZE
                else PruefungsStatus.NICHT_BESTANDEN
            )
        else:
            pruefungsstatus = PruefungsStatus.OFFEN

        datum_text = wert("Frist/Datum")
        relevantes_datum: date | None = None
        if datum_text:
            try:
                relevantes_datum = date.fromisoformat(datum_text)
            except ValueError as fehlerursache:
                raise ValueError(
                    f"Spalte 'Frist/Datum' muss im Format JJJJ-MM-TT sein, war '{datum_text}'."
                ) from fehlerursache

        return CsvZeile(
            semester_nummer=semester_nummer,
            modultitel=modultitel,
            kurs_id=wert("Kurs-ID") or None,
            ects=ects,
            modul_status=modul_status,
            pruefungstitel=pruefungstitel,
            art=art,
            status=pruefungsstatus,
            relevantes_datum=relevantes_datum,
            max_punkte=max_punkte,
            punkte=punkte,
            note=note,
        )

    @staticmethod
    def _zu_int(wert: str, spalte: str) -> int:
        try:
            return int(wert)
        except ValueError as fehlerursache:
            raise ValueError(
                f"Spalte '{spalte}' muss eine Ganzzahl sein, war '{wert}'."
            ) from fehlerursache

    @staticmethod
    def _zu_optionale_zahl(wert: str, spalte: str) -> float | None:
        if not wert:
            return None
        try:
            return float(wert.replace(",", "."))
        except ValueError as fehlerursache:
            raise ValueError(
                f"Spalte '{spalte}' muss eine Zahl sein, war '{wert}'."
            ) from fehlerursache

    @staticmethod
    def _zu_enum(enum_cls: type[_EnumTyp], wert: str, spalte: str) -> _EnumTyp:
        try:
            return enum_cls(wert.strip().lower())  # type: ignore[call-arg]
        except ValueError as fehlerursache:
            erlaubt = ", ".join(eintrag.value for eintrag in enum_cls)  # type: ignore[attr-defined]
            raise ValueError(
                f"Spalte '{spalte}' hat ungültigen Wert '{wert}'. Erlaubt sind: {erlaubt}."
            ) from fehlerursache
