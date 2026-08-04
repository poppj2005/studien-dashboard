"""Hilfsfunktion zum Aufbau eines konsistenten Beispiel-Studenten für Tests."""

from __future__ import annotations

from datetime import date

from src.domain.enums import ModulStatus, Pruefungsart, PruefungsStatus
from src.domain.modelle import Modul, Pruefungsleistung, Semester, Student, Studiengang
from src.domain.ziele import EctsZiel, FristenZiel, NotenZiel


def erstelle_beispiel_student() -> Student:
    """Baut einen kleinen Studenten mit einem abgeschlossenen und einem offenen Modul.

    Modul A (5 ECTS) ist abgeschlossen und mit Note 2.0 bestanden.
    Modul B (10 ECTS) ist aktiv und hat eine angemeldete Klausur am 2026-01-20.
    """
    studiengang = Studiengang(
        name="Testgang",
        semester=[
            Semester(
                nummer=1,
                module=[
                    Modul(
                        titel="Modul A",
                        ects=5,
                        status=ModulStatus.ABGESCHLOSSEN,
                        kurs_id="MA01",
                        pruefungsleistungen=[
                            Pruefungsleistung(
                                titel="Klausur A",
                                art=Pruefungsart.KLAUSUR,
                                status=PruefungsStatus.BESTANDEN,
                                note=2.0,
                                punkte=87.5,
                                max_punkte=100.0,
                                relevantes_datum=date(2025, 10, 1),
                            )
                        ],
                    ),
                    Modul(
                        titel="Modul B",
                        ects=10,
                        status=ModulStatus.AKTIV,
                        pruefungsleistungen=[
                            Pruefungsleistung(
                                titel="Klausur B",
                                art=Pruefungsart.KLAUSUR,
                                status=PruefungsStatus.ANGEMELDET,
                                relevantes_datum=date(2026, 1, 20),
                            )
                        ],
                    ),
                ],
            )
        ],
    )
    return Student(
        name="Test Student",
        studiengang=studiengang,
        ects_ziel=EctsZiel(bezeichnung="ECTS-Fortschritt", ziel_ects=15),
        noten_ziel=NotenZiel(bezeichnung="Notendurchschnitt", ziel_notenschnitt=2.5),
        fristen_ziel=FristenZiel(bezeichnung="Fristen", warnschwelle_tage=14),
    )
