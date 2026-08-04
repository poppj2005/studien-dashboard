"""Controller-Schicht: vermittelt zwischen Tkinter-View, Services und Repository."""

from __future__ import annotations

from pathlib import Path

from src.domain.enums import PruefungsStatus
from src.domain.exceptions import (
    ModulBereitsVorhandenError,
    ModulNichtGefundenError,
    PruefungsleistungNichtGefundenError,
    SemesterNichtGefundenError,
)
from src.domain.modelle import NOTE_BESTEHENSGRENZE, Modul, Pruefungsleistung, Semester, Student
from src.dto.ausgabe_dtos import DashboardDatenDTO
from src.dto.eingabe_dtos import ModulAnlageDTO, PruefungsUpdateDTO
from src.repository.json_repository import StudentRepository
from src.services.csv_import_service import CsvImportService
from src.services.dashboard_service import DashboardService


class DashboardController:
    """Dünne Orchestrierungsschicht ohne eigene Fachlogik in den Services.

    Hält den geladenen Studenten im Speicher; jede Aktualisierung sucht die
    passende Prüfungsleistung über Modultitel und Prüfungstitel, ändert
    nur die im DTO gesetzten Werte und persistiert danach den Studenten.
    Existiert Modul oder Prüfungsleistung noch nicht, werden sie aus den
    zusätzlichen DTO-Feldern neu angelegt (siehe PruefungsUpdateDTO).
    """

    def __init__(
        self,
        repository: StudentRepository,
        dashboard_service: DashboardService,
        csv_import_service: CsvImportService,
    ) -> None:
        self._repository = repository
        self._dashboard_service = dashboard_service
        self._csv_import_service = csv_import_service
        self._student: Student = repository.lade_student()

    def lade_dashboard(self) -> DashboardDatenDTO:
        """Liefert die aktuellen, aggregierten Dashboard-Daten aus dem Speicher.

        Liest nicht erneut von der Persistenz – wird intern nach eigenen
        Änderungen aufgerufen, die bereits im geladenen Studenten stecken.
        Für ein Neuladen von der Datei siehe lade_neu().
        """
        return self._dashboard_service.erstelle_dashboard(self._student)

    def lade_neu(self) -> DashboardDatenDTO:
        """Lädt den Studenten frisch von der Persistenz und liefert das Dashboard dazu.

        Nötig, damit z. B. der "Neu laden"-Button auch externe Änderungen an
        der Datei sieht – der Controller hält sonst nur den einmal beim
        Start geladenen Studenten im Speicher.
        """
        self._student = self._repository.lade_student()
        return self.lade_dashboard()

    def aktualisiere_pruefung(self, update: PruefungsUpdateDTO) -> DashboardDatenDTO:
        """Aktualisiert eine Prüfungsleistung – oder legt sie samt Modul neu an.

        Raises:
            ModulNichtGefundenError: wenn kein Modul mit update.modultitel existiert
                und update.ects/semester_nummer nicht gesetzt sind, um es neu anzulegen.
            PruefungsleistungNichtGefundenError: wenn das Modul keine
                Prüfungsleistung mit update.pruefungstitel besitzt und
                update.art nicht gesetzt ist, um sie neu anzulegen.
        """
        modul = self._finde_oder_erstelle_modul(update)
        if update.modul_status is not None:
            modul.status = update.modul_status

        pruefungsleistung = self._finde_oder_erstelle_pruefungsleistung(modul, update)

        if update.note is not None:
            pruefungsleistung.note = update.note
        if update.punkte is not None:
            pruefungsleistung.punkte = update.punkte
        if update.status is not None:
            pruefungsleistung.status = update.status
        elif update.note is not None:
            # Kein Status gesetzt, aber eine Note eingetragen: Status aus der Note
            # ableiten, sonst bliebe die Prüfung z. B. auf "angemeldet" stehen und
            # würde nicht als bestanden – und damit nicht in den ECTS – gezählt.
            pruefungsleistung.status = (
                PruefungsStatus.BESTANDEN
                if update.note <= NOTE_BESTEHENSGRENZE
                else PruefungsStatus.NICHT_BESTANDEN
            )
        if update.relevantes_datum is not None:
            pruefungsleistung.relevantes_datum = update.relevantes_datum

        self._repository.speichere(self._student)
        return self.lade_dashboard()

    def lege_modul_an(self, eingabe: ModulAnlageDTO) -> DashboardDatenDTO:
        """Legt ein Modul direkt an – oder bearbeitet ein bestehendes.

        Existiert bereits ein Modul mit eingabe.titel, werden ects, status
        (falls gesetzt) und ein neuer Titel (falls gesetzt) übernommen, statt
        ein zweites Modul anzulegen.

        Raises:
            ModulNichtGefundenError: wenn eingabe.titel noch nicht existiert
                und eingabe.semester_nummer nicht gesetzt ist, um es neu anzulegen.
            ModulBereitsVorhandenError: wenn eingabe.neuer_titel bereits von
                einem anderen Modul verwendet wird.
        """
        modul = self._finde_modul(eingabe.titel)
        if modul is None:
            if eingabe.semester_nummer is None:
                raise ModulNichtGefundenError(
                    f"Kein Modul mit dem Titel '{eingabe.titel}' gefunden. Für ein neues "
                    "Modul wird die Semesternummer benötigt."
                )
            semester = self._finde_oder_erstelle_semester(eingabe.semester_nummer)
            modul = Modul(titel=eingabe.titel, ects=eingabe.ects)
            semester.module.append(modul)
        else:
            modul.ects = eingabe.ects
            if eingabe.neuer_titel is not None and eingabe.neuer_titel != modul.titel:
                if self._finde_modul(eingabe.neuer_titel) is not None:
                    raise ModulBereitsVorhandenError(
                        f"Es existiert bereits ein Modul mit dem Titel '{eingabe.neuer_titel}'."
                    )
                modul.titel = eingabe.neuer_titel

        if eingabe.status is not None:
            modul.status = eingabe.status

        self._repository.speichere(self._student)
        return self.lade_dashboard()

    def loesche_modul(self, titel: str) -> DashboardDatenDTO:
        """Löscht ein Modul samt allen seinen Prüfungsleistungen.

        Raises:
            ModulNichtGefundenError: wenn kein Modul mit diesem Titel existiert.
        """
        for semester in self._student.studiengang.semester:
            for modul in semester.module:
                if modul.titel == titel:
                    semester.module.remove(modul)
                    self._repository.speichere(self._student)
                    return self.lade_dashboard()
        raise ModulNichtGefundenError(f"Kein Modul mit dem Titel '{titel}' gefunden.")

    def loesche_pruefungsleistung(self, modultitel: str, pruefungstitel: str) -> DashboardDatenDTO:
        """Löscht eine einzelne Prüfungsleistung aus ihrem Modul.

        Raises:
            ModulNichtGefundenError: wenn kein Modul mit modultitel existiert.
            PruefungsleistungNichtGefundenError: wenn das Modul keine
                Prüfungsleistung mit pruefungstitel besitzt.
        """
        modul = self._finde_modul(modultitel)
        if modul is None:
            raise ModulNichtGefundenError(f"Kein Modul mit dem Titel '{modultitel}' gefunden.")

        for pruefungsleistung in modul.pruefungsleistungen:
            if pruefungsleistung.titel == pruefungstitel:
                modul.pruefungsleistungen.remove(pruefungsleistung)
                self._repository.speichere(self._student)
                return self.lade_dashboard()
        raise PruefungsleistungNichtGefundenError(
            f"Modul '{modultitel}' hat keine Prüfungsleistung mit dem Titel '{pruefungstitel}'."
        )

    def loesche_semester(self, nummer: int) -> DashboardDatenDTO:
        """Löscht ein Semester samt aller enthaltenen Module und Prüfungsleistungen.

        Raises:
            SemesterNichtGefundenError: wenn kein Semester mit dieser Nummer existiert.
        """
        for semester in self._student.studiengang.semester:
            if semester.nummer == nummer:
                self._student.studiengang.semester.remove(semester)
                self._repository.speichere(self._student)
                return self.lade_dashboard()
        raise SemesterNichtGefundenError(f"Kein Semester mit der Nummer '{nummer}' gefunden.")

    def importiere_csv(self, datei_pfad: Path) -> DashboardDatenDTO:
        """Importiert Semester/Module/Prüfungsleistungen aus einer CSV-Datei.

        Die Datei wird zuerst vollständig validiert (CsvImportService) und erst
        danach übernommen – entweder komplett oder gar nicht. Module und
        Prüfungsleistungen werden wie bei den manuellen Pflege-Methoden über
        ihren Titel gefunden oder neu angelegt.

        Raises:
            CsvImportError: wenn die Datei fehlende Spalten oder ungültige Werte enthält.
        """
        zeilen = self._csv_import_service.lade_zeilen(datei_pfad)
        for zeile in zeilen:
            semester = self._finde_oder_erstelle_semester(zeile.semester_nummer)
            modul = self._finde_modul(zeile.modultitel)
            if modul is None:
                modul = Modul(titel=zeile.modultitel, ects=zeile.ects, kurs_id=zeile.kurs_id)
                semester.module.append(modul)
            else:
                modul.ects = zeile.ects
                modul.kurs_id = zeile.kurs_id
            modul.status = zeile.modul_status

            pruefungsleistung = next(
                (p for p in modul.pruefungsleistungen if p.titel == zeile.pruefungstitel), None
            )
            if pruefungsleistung is None:
                pruefungsleistung = Pruefungsleistung(titel=zeile.pruefungstitel, art=zeile.art)
                modul.pruefungsleistungen.append(pruefungsleistung)
            pruefungsleistung.art = zeile.art
            pruefungsleistung.status = zeile.status
            if zeile.note is not None:
                pruefungsleistung.note = zeile.note
            if zeile.punkte is not None:
                pruefungsleistung.punkte = zeile.punkte
            if zeile.max_punkte is not None:
                pruefungsleistung.max_punkte = zeile.max_punkte
            if zeile.relevantes_datum is not None:
                pruefungsleistung.relevantes_datum = zeile.relevantes_datum

        self._repository.speichere(self._student)
        return self.lade_dashboard()

    def setze_dashboard_zurueck(self) -> DashboardDatenDTO:
        """Setzt das komplette Dashboard zurück: entfernt alle Semester, Module
        und Prüfungsleistungen. Die drei Studienziele bleiben erhalten, da sie
        Vorgaben und keine erfassten Fortschrittsdaten sind.
        """
        self._student.studiengang.semester = []
        self._repository.speichere(self._student)
        return self.lade_dashboard()

    def _finde_modul(self, titel: str) -> Modul | None:
        for semester in self._student.studiengang.semester:
            for modul in semester.module:
                if modul.titel == titel:
                    return modul
        return None

    def _finde_oder_erstelle_modul(self, update: PruefungsUpdateDTO) -> Modul:
        modul = self._finde_modul(update.modultitel)
        if modul is not None:
            return modul

        if update.ects is None or update.semester_nummer is None:
            raise ModulNichtGefundenError(
                f"Kein Modul mit dem Titel '{update.modultitel}' gefunden. Für ein neues "
                "Modul werden ECTS und Semesternummer benötigt."
            )
        semester = self._finde_oder_erstelle_semester(update.semester_nummer)
        modul = Modul(titel=update.modultitel, ects=update.ects)
        semester.module.append(modul)
        return modul

    def _finde_oder_erstelle_semester(self, nummer: int) -> Semester:
        for semester in self._student.studiengang.semester:
            if semester.nummer == nummer:
                return semester
        semester = Semester(nummer=nummer)
        self._student.studiengang.semester.append(semester)
        self._student.studiengang.semester.sort(key=lambda s: s.nummer)
        return semester

    def _finde_oder_erstelle_pruefungsleistung(
        self, modul: Modul, update: PruefungsUpdateDTO
    ) -> Pruefungsleistung:
        for pruefungsleistung in modul.pruefungsleistungen:
            if pruefungsleistung.titel == update.pruefungstitel:
                return pruefungsleistung

        if update.art is None:
            raise PruefungsleistungNichtGefundenError(
                f"Modul '{modul.titel}' hat keine Prüfungsleistung mit dem Titel "
                f"'{update.pruefungstitel}'. Für eine neue Prüfungsleistung wird die "
                "Prüfungsart benötigt."
            )
        pruefungsleistung = Pruefungsleistung(titel=update.pruefungstitel, art=update.art)
        modul.pruefungsleistungen.append(pruefungsleistung)
        return pruefungsleistung
