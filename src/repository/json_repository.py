"""Repository-Schicht: persistiert den Studenten in einer JSON-Datei.

Kapselt sämtliche Serialisierungsdetails (Enums, Datumswerte, verschachtelte
Objekte) an einer Stelle, damit Service- und Controller-Schicht
ausschließlich mit Domänenobjekten arbeiten.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

from src.domain.enums import ModulStatus, Pruefungsart, PruefungsStatus
from src.domain.modelle import Modul, Pruefungsleistung, Semester, Student, Studiengang
from src.domain.ziele import EctsZiel, FristenZiel, NotenZiel


class StudentRepository(ABC):
    """Abstrakte Schnittstelle für die Persistenz eines Studenten."""

    @abstractmethod
    def lade_student(self) -> Student:
        """Lädt den vollständigen Studenten aus dem Speicher."""

    @abstractmethod
    def speichere(self, student: Student) -> None:
        """Speichert den vollständigen Studenten."""


class JsonStudentRepository(StudentRepository):
    """Liest und schreibt den Studenten als JSON-Datei unter data/student.json.

    Existiert die Datei noch nicht (z. B. bei einem frischen Checkout),
    erzeugt lade_student() eine sinnvolle Beispieldatei, damit der
    Prototyp ohne manuelle Vorbereitung startet.
    """

    def __init__(self, datei_pfad: Path) -> None:
        self._datei_pfad = datei_pfad

    def lade_student(self) -> Student:
        """Lädt den Studenten aus der JSON-Datei und erstellt bei Bedarf Beispieldaten."""
        if not self._datei_pfad.exists():
            self._datei_pfad.parent.mkdir(parents=True, exist_ok=True)
            self.speichere(self._erzeuge_beispiel_student())
        with self._datei_pfad.open("r", encoding="utf-8") as datei:
            rohdaten = json.load(datei)
        return self._zu_student(rohdaten)

    def speichere(self, student: Student) -> None:
        """Speichert den Studenten als JSON-Datei inklusive aller verschachtelten Daten."""
        rohdaten = self._zu_dict(student)
        with self._datei_pfad.open("w", encoding="utf-8") as datei:
            json.dump(rohdaten, datei, indent=2, ensure_ascii=False)

    # -- Deserialisierung ----------------------------------------------------

    @staticmethod
    def _parse_datum(wert: str | None) -> date | None:
        return date.fromisoformat(wert) if wert else None

    @staticmethod
    def _datum_zu_str(wert: date | None) -> str | None:
        return wert.isoformat() if wert else None

    def _zu_student(self, rohdaten: dict) -> Student:
        studiengang_rohdaten = rohdaten["studiengang"]
        semester = [
            Semester(
                nummer=s["nummer"],
                module=[self._zu_modul(m) for m in s.get("module", [])],
            )
            for s in studiengang_rohdaten.get("semester", [])
        ]
        studiengang = Studiengang(name=studiengang_rohdaten["name"], semester=semester)

        ects_ziel_rohdaten = rohdaten["ects_ziel"]
        ects_ziel = EctsZiel(
            bezeichnung=ects_ziel_rohdaten.get("bezeichnung", "ECTS-Ziel"),
            ziel_ects=ects_ziel_rohdaten["ziel_ects"],
            ziel_datum=self._parse_datum(ects_ziel_rohdaten.get("ziel_datum")),
        )
        noten_ziel_rohdaten = rohdaten["noten_ziel"]
        noten_ziel = NotenZiel(
            bezeichnung=noten_ziel_rohdaten.get("bezeichnung", "Notenziel"),
            ziel_notenschnitt=noten_ziel_rohdaten["ziel_notenschnitt"],
        )
        fristen_ziel_rohdaten = rohdaten["fristen_ziel"]
        fristen_ziel = FristenZiel(
            bezeichnung=fristen_ziel_rohdaten.get("bezeichnung", "Fristenziel"),
            warnschwelle_tage=fristen_ziel_rohdaten.get("warnschwelle_tage", 14),
        )

        return Student(
            name=rohdaten["name"],
            studiengang=studiengang,
            ects_ziel=ects_ziel,
            noten_ziel=noten_ziel,
            fristen_ziel=fristen_ziel,
        )

    def _zu_modul(self, rohdaten: dict) -> Modul:
        return Modul(
            titel=rohdaten["titel"],
            ects=rohdaten["ects"],
            status=ModulStatus(rohdaten["status"]),
            kurs_id=rohdaten.get("kurs_id"),
            pruefungsleistungen=[
                self._zu_pruefungsleistung(p) for p in rohdaten.get("pruefungsleistungen", [])
            ],
        )

    def _zu_pruefungsleistung(self, rohdaten: dict) -> Pruefungsleistung:
        return Pruefungsleistung(
            titel=rohdaten["titel"],
            art=Pruefungsart(rohdaten["art"]),
            status=PruefungsStatus(rohdaten["status"]),
            note=rohdaten.get("note"),
            punkte=rohdaten.get("punkte"),
            max_punkte=rohdaten.get("max_punkte"),
            relevantes_datum=self._parse_datum(rohdaten.get("relevantes_datum")),
        )

    # -- Serialisierung --------------------------------------------------------

    def _zu_dict(self, student: Student) -> dict:
        return {
            "name": student.name,
            "studiengang": {
                "name": student.studiengang.name,
                "semester": [
                    {
                        "nummer": semester.nummer,
                        "module": [self._modul_zu_dict(m) for m in semester.module],
                    }
                    for semester in student.studiengang.semester
                ],
            },
            "ects_ziel": {
                "bezeichnung": student.ects_ziel.bezeichnung,
                "ziel_ects": student.ects_ziel.ziel_ects,
                "ziel_datum": self._datum_zu_str(student.ects_ziel.ziel_datum),
            },
            "noten_ziel": {
                "bezeichnung": student.noten_ziel.bezeichnung,
                "ziel_notenschnitt": student.noten_ziel.ziel_notenschnitt,
            },
            "fristen_ziel": {
                "bezeichnung": student.fristen_ziel.bezeichnung,
                "warnschwelle_tage": student.fristen_ziel.warnschwelle_tage,
            },
        }

    def _modul_zu_dict(self, modul: Modul) -> dict:
        return {
            "titel": modul.titel,
            "ects": modul.ects,
            "status": modul.status.value,
            "kurs_id": modul.kurs_id,
            "pruefungsleistungen": [
                {
                    "titel": p.titel,
                    "art": p.art.value,
                    "status": p.status.value,
                    "note": p.note,
                    "punkte": p.punkte,
                    "max_punkte": p.max_punkte,
                    "relevantes_datum": self._datum_zu_str(p.relevantes_datum),
                }
                for p in modul.pruefungsleistungen
            ],
        }

    # -- Beispieldaten für den Erststart ---------------------------------------

    @staticmethod
    def _erzeuge_beispiel_student() -> Student:
        """Baut einen plausiblen Beispiel-Studenten, falls noch keine Datei existiert."""
        studiengang = Studiengang(
            name="B.Sc. Wirtschaftsinformatik",
            semester=[
                Semester(
                    nummer=4,
                    module=[
                        Modul(
                            titel="Objektorientierte Programmierung",
                            ects=5,
                            status=ModulStatus.AKTIV,
                            pruefungsleistungen=[
                                Pruefungsleistung(
                                    titel="Portfolio OOP",
                                    art=Pruefungsart.PORTFOLIO,
                                    status=PruefungsStatus.ANGEMELDET,
                                    relevantes_datum=date(2026, 8, 15),
                                )
                            ],
                        ),
                        Modul(
                            titel="Statistik",
                            ects=5,
                            status=ModulStatus.ABGESCHLOSSEN,
                            pruefungsleistungen=[
                                Pruefungsleistung(
                                    titel="Klausur Statistik",
                                    art=Pruefungsart.KLAUSUR,
                                    status=PruefungsStatus.BESTANDEN,
                                    note=2.0,
                                    relevantes_datum=date(2025, 12, 10),
                                )
                            ],
                        ),
                    ],
                ),
                Semester(
                    nummer=5,
                    module=[
                        Modul(
                            titel="IT-Management",
                            ects=5,
                            status=ModulStatus.GEPLANT,
                            pruefungsleistungen=[
                                Pruefungsleistung(
                                    titel="Klausur IT-Management",
                                    art=Pruefungsart.KLAUSUR,
                                    status=PruefungsStatus.ANGEMELDET,
                                    relevantes_datum=date(2026, 7, 28),
                                )
                            ],
                        ),
                        Modul(
                            titel="Datenbanken",
                            ects=5,
                            status=ModulStatus.GEPLANT,
                            pruefungsleistungen=[
                                Pruefungsleistung(
                                    titel="Klausur Datenbanken",
                                    art=Pruefungsart.KLAUSUR,
                                    status=PruefungsStatus.OFFEN,
                                )
                            ],
                        ),
                    ],
                ),
                Semester(
                    nummer=6,
                    module=[
                        Modul(
                            titel="Projektmodul",
                            ects=10,
                            status=ModulStatus.GEPLANT,
                            pruefungsleistungen=[
                                Pruefungsleistung(
                                    titel="Projektarbeit",
                                    art=Pruefungsart.PROJEKT,
                                    status=PruefungsStatus.OFFEN,
                                )
                            ],
                        ),
                    ],
                ),
            ],
        )
        return Student(
            name="Max Mustermann",
            studiengang=studiengang,
            ects_ziel=EctsZiel(bezeichnung="ECTS-Fortschritt", ziel_ects=180),
            noten_ziel=NotenZiel(bezeichnung="Notendurchschnitt", ziel_notenschnitt=2.0),
            fristen_ziel=FristenZiel(bezeichnung="Fristen", warnschwelle_tage=14),
        )
