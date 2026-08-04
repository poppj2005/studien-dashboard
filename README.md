# Studien-Dashboard (Prototyp)

Ein Tkinter-basiertes Dashboard für ein Fernstudium. Die Daten werden manuell
in einer JSON-Datei gepflegt – es gibt keine Datenbank und keine externe API.
Der Prototyp ist so gebaut, dass er ohne Installation zusätzlicher Pakete
auf einem aktuellen Windows-System getestet werden kann.

## Fachliche Ziele

1. ECTS-Fortschritt überwachen
2. Notendurchschnitt überwachen
3. Prüfungsorganisation: offene Prüfungen und den nächsten relevanten Termin überwachen

## Voraussetzungen

- Python 3.10 oder neuer (inkl. Tkinter – bei den offiziellen Python-Installern
  für Windows ist Tkinter standardmäßig enthalten)
- Ausschließlich die Python-Standardbibliothek, siehe [requirements.txt](requirements.txt)

## Installation unter Windows

1. Python von [python.org](https://www.python.org/downloads/windows/) installieren
   (Option "Add python.exe to PATH" beim Setup aktivieren).
2. Projektordner herunterladen bzw. klonen (siehe GitHub-Link unten).
3. In der Eingabeaufforderung in den Projektordner wechseln:
   ```bat
   cd Pfad\zum\studien-dashboard
   ```
4. Keine weitere Installation nötig, da nur die Standardbibliothek verwendet wird.

## Start

```bash
python main.py
```

Beim ersten Start wird [data/student.json](data/student.json) verwendet; existiert die
Datei nicht, erzeugt das Repository automatisch eine sinnvolle Beispieldatei.

## Tests ausführen

```bash
python -m unittest discover tests
```

## Beispiel-CSV

Eine Musterdatei für den CSV-Import liegt im Projekt unter `data/beispiel_import.csv`. Diese Datei kann verwendet werden, um die Importfunktion des Dashboards direkt zu testen.

## GitHub

Repository-Link: `https://github.com/poppj2005/studien-dashboard`

## Projektstruktur

```
studien-dashboard/
├── main.py                        Einstiegspunkt
├── data/
│   └── student.json               Manuell gepflegte Studiendaten
├── src/
│   ├── app.py                     DashboardApp: verdrahtet alle Schichten
│   ├── domain/
│   │   ├── enums.py                 ModulStatus, PruefungsStatus, Pruefungsart, AmpelStatus
│   │   ├── ziele.py                 Studienziel (abstrakt), EctsZiel, NotenZiel, FristenZiel
│   │   ├── modelle.py                Student, Studiengang, Semester, Modul, Pruefungsleistung
│   │   └── exceptions.py            ModulNichtGefundenError, PruefungsleistungNichtGefundenError
│   ├── dto/
│   │   ├── eingabe_dtos.py          PruefungsUpdateDTO
│   │   └── ausgabe_dtos.py          DashboardDatenDTO, ZielAmpelDTO, ModulUebersichtDTO
│   ├── repository/
│   │   └── json_repository.py       StudentRepository, JsonStudentRepository
│   ├── services/
│   │   ├── fortschritts_service.py  FortschrittsService
│   │   ├── noten_service.py         NotenService
│   │   ├── fristen_service.py       FristenService
│   │   └── dashboard_service.py     DashboardService
│   ├── controller/
│   │   └── dashboard_controller.py  DashboardController
│   └── view/
│       └── tkinter_view.py          TkinterDashboardView
└── tests/
    ├── testdaten.py                 Gemeinsame Testdaten-Fabrik
    ├── test_fortschritts_service.py
    ├── test_noten_service.py
    ├── test_fristen_service.py
    ├── test_repository.py
    └── test_controller.py
```

## Bedienungsanleitung

1. Nach dem Start zeigt der Kopfbereich Studentin/Student und Studiengang.
2. Die vier Kacheln zeigen ECTS-Fortschritt, Notendurchschnitt, Prüfungsstatus
   (offen/angemeldet) und die nächste relevante Frist.
3. Der Fortschrittsbalken zeigt Ist-ECTS gegenüber dem Ziel; die Zielampel
   fasst ECTS-, Noten- und Fristenbewertung farblich zusammen (grün/gelb/rot).
4. Die Tabelle listet alle Module mit ihren Prüfungsleistungen auf.
5. Im Bereich "Prüfungsleistung aktualisieren" Modulnummer und Prüfungstitel
   auswählen (ein Klick auf eine Tabellenzeile befüllt beide Felder
   automatisch), optional Status, Note und/oder Datum setzen und auf
   "Aktualisieren" klicken. Nur ausgefüllte Felder werden geändert;
   anschließend wird automatisch gespeichert und die Ansicht neu geladen.

## Architektur- und Datenmodell-Entscheidungen

- **`EctsZiel` ist die einzige Quelle für `ziel_ects`** – weder Studiengang
  noch Student speichern das Ziel zusätzlich, um Inkonsistenzen zu vermeiden.
- **Kein gespeichertes `bewertet`-Feld** – `Pruefungsleistung.ist_bewertet` ist
  eine abgeleitete Property auf Basis von `note` und `status`.
- **Kein `frist`-Feld** – Prüfungsleistungen tragen `relevantes_datum: date | None`,
  da es je nach Prüfungsart ein Klausurtermin oder ein Abgabedatum ist.
- **`note` ist optional** (`float | None`), ebenso `DashboardDatenDTO.notenschnitt`
  und `naechster_termin` – ein fehlender Wert wird nicht durch einen
  irreführenden Platzhalter verdeckt.
- **`DashboardController.aktualisiere_pruefung`** nimmt ein typisiertes
  `PruefungsUpdateDTO` entgegen statt einzelner loser Parameter oder eines dict.
- **`TkinterDashboardView`** baut aus den Formularfeldern stets ein
  `PruefungsUpdateDTO` – nie ein unstrukturiertes dict.
- **`ZielAmpelDTO`** ersetzt ein generisches dict durch drei typisierte Felder
  (`ects`, `noten`, `fristen: AmpelStatus`).
- **`Studienziel`** ist eine abstrakte Basisklasse; `EctsZiel`, `NotenZiel` und
  `FristenZiel` sind konkrete Ausprägungen. Student hält sie als eigene,
  typisierte Felder (nicht als generische Liste), damit die Services ohne
  Typprüfung direkt zugreifen können.
- **`ModulUebersichtDTO`** (Modul + `semester_nummer`) wurde ergänzt, damit die
  Tabelle die Semesterzuordnung anzeigen kann, ohne diese zusätzlich und
  redundant am `Modul` selbst zu speichern – die Zuordnung wird beim Aufbau
  des Dashboards aus `Studiengang.semester` abgeleitet.
- **Fehlende Beispieldatei**: `JsonStudentRepository.lade_student()` erzeugt
  automatisch eine plausible Beispieldatei, falls `data/student.json` noch
  nicht existiert (z. B. bei einem frischen Checkout).
- **Fehlerbehandlung bei Aktualisierung**: Werden Modulnummer oder
  Prüfungstitel nicht gefunden, wirft der Controller `ModulNichtGefundenError`
  bzw. `PruefungsleistungNichtGefundenError` mit verständlicher Meldung; die
  View fängt beide ab und zeigt sie im Fehlerdialog an.
