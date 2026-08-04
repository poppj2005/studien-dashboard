"""Tkinter-View: stellt das Dashboard im Karten-Layout dar.

Baut aus den Formularfeldern stets ein typisiertes PruefungsUpdateDTO
und reicht nie ein unstrukturiertes dict an den Controller weiter.
"""

from __future__ import annotations

import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from src.controller.dashboard_controller import DashboardController
from src.domain.enums import AmpelStatus, ModulStatus, Pruefungsart, PruefungsStatus
from src.domain.exceptions import (
    CsvImportError,
    ModulBereitsVorhandenError,
    ModulNichtGefundenError,
    PruefungsleistungNichtGefundenError,
    SemesterNichtGefundenError,
)
from src.domain.modelle import ECTS_VORSCHLAG, NOTE_MAX, NOTE_MIN
from src.dto.ausgabe_dtos import DashboardDatenDTO
from src.dto.eingabe_dtos import ModulAnlageDTO, PruefungsUpdateDTO

_NAVY = "#1b2a4a"
_HINTERGRUND = "#f7f8fa"
_CARD_BLAU = "#dceafc"
_CARD_GELB = "#fdf3c8"
_CARD_ROT = "#fbe2e2"
_CARD_GRAU = "#eef0f3"
_AKZENT_BLAU = "#1e3a5f"
_AKZENT_BLAU_HOVER = "#16293f"
_BADGE_FARBEN = {
    AmpelStatus.GRUEN: ("#e0f3e3", "#1f7a34"),
    AmpelStatus.GELB: ("#fdf1c7", "#8a6d1a"),
    AmpelStatus.ROT: ("#fbdede", "#b23b3b"),
}

_FONT = "Helvetica"
_FONT_TITEL = (_FONT, 17, "bold")
_FONT_UEBERSCHRIFT = (_FONT, 10, "bold")
_FONT_TEXT = (_FONT, 10)
_FONT_KLEIN = (_FONT, 9)
_FONT_WERT = (_FONT, 22, "bold")
_FONT_BUTTON = (_FONT, 11, "bold")


class TkinterDashboardView(tk.Tk):
    """Hauptfenster des Studien-Dashboards."""

    def __init__(self, controller: DashboardController) -> None:
        super().__init__()
        self._controller = controller
        self.title("Studien-Dashboard")
        self.configure(bg=_HINTERGRUND)
        self._zentriere_fenster(1160, 860)

        # modultitel -> Liste der Prüfungstitel dieses Moduls (für die Auswahl im Formular)
        self._pruefungstitel_by_modultitel: dict[str, list[str]] = {}
        # modultitel -> (ects, status) des Moduls, um das Modul-Formular per Klick zu befüllen
        self._modul_info_by_titel: dict[str, tuple[int, ModulStatus]] = {}
        self._ampel_badges: dict[str, tuple[tk.Label, str]] = {}

        self._baue_header()
        self._baue_aktionsleiste()
        self._baue_scrollbereich()

        self._baue_kpi_zeile()
        self._baue_mittlere_zeile()
        self._baue_tabelle()
        self._baue_semester_bereich()
        self._baue_modul_anlegen_bereich()
        self._baue_eingabebereich()

        self.aktualisiere_ansicht()

    # -- Aufbau der Widgets --------------------------------------------------

    def _zentriere_fenster(self, breite: int, hoehe: int) -> None:
        """Zentriert das Fenster auf dem Bildschirm statt es links oben zu platzieren."""
        self.update_idletasks()
        x = max((self.winfo_screenwidth() - breite) // 2, 0)
        y = max((self.winfo_screenheight() - hoehe) // 2, 0)
        self.geometry(f"{breite}x{hoehe}+{x}+{y}")

    def _baue_aktionsleiste(self) -> None:
        """Gut sichtbare, zentrierte Leiste mit den dashboardweiten Aktionen
        CSV-Import und komplettes Zurücksetzen – bewusst außerhalb des
        scrollbaren Bereichs, damit sie immer erreichbar bleibt.

        Nutzt Label-basierte "Buttons" statt tk.Button: unter macOS/Aqua
        ignoriert das native tk.Button-Rendering die bg/fg-Farben komplett
        (bekannte Tk-Einschränkung), ein Label mit Klick-Bindung zeigt die
        Farben dagegen zuverlässig an.
        """
        leiste = tk.Frame(self, bg=_HINTERGRUND)
        leiste.pack(fill=tk.X, pady=(12, 0))

        innen = tk.Frame(leiste, bg=_HINTERGRUND)
        innen.pack(anchor="center")

        self._erstelle_aktions_button(
            innen,
            text="⭱  CSV importieren",
            befehl=self._auf_csv_importieren_geklickt,
            hintergrund=_AKZENT_BLAU,
            hover_hintergrund=_AKZENT_BLAU_HOVER,
        ).pack(side=tk.LEFT, padx=8)

        self._erstelle_aktions_button(
            innen,
            text="↺  Dashboard zurücksetzen",
            befehl=self._auf_dashboard_zuruecksetzen_geklickt,
            hintergrund=_AKZENT_BLAU,
            hover_hintergrund=_AKZENT_BLAU_HOVER,
        ).pack(side=tk.LEFT, padx=8)

    @staticmethod
    def _erstelle_aktions_button(
        eltern: tk.Widget,
        text: str,
        befehl: object,
        hintergrund: str,
        hover_hintergrund: str,
    ) -> tk.Label:
        button = tk.Label(
            eltern,
            text=text,
            font=_FONT_BUTTON,
            bg=hintergrund,
            fg="white",
            padx=20,
            pady=10,
            cursor="pointinghand",
        )
        button.bind("<Button-1>", lambda _e: befehl())
        button.bind("<Enter>", lambda _e: button.config(bg=hover_hintergrund))
        button.bind("<Leave>", lambda _e: button.config(bg=hintergrund))
        return button

    def _baue_scrollbereich(self) -> None:
        """Macht alles unterhalb des Headers scrollbar, damit auch bei kleinen
        Bildschirmen jeder Bereich erreichbar bleibt (Fenster passt sonst nicht
        immer komplett auf den Bildschirm)."""
        canvas = tk.Canvas(self, bg=_HINTERGRUND, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self._scroll_rahmen = tk.Frame(canvas, bg=_HINTERGRUND)

        self._scroll_rahmen.bind(
            "<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        fenster_id = canvas.create_window((0, 0), window=self._scroll_rahmen, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(fenster_id, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._canvas = canvas
        ist_mac = self.tk.call("tk", "windowingsystem") == "aqua"
        self.bind_all(
            "<MouseWheel>",
            lambda e: canvas.yview_scroll(
                int(-1 * e.delta) if ist_mac else int(-1 * (e.delta / 120)), "units"
            ),
        )
        self.bind_all("<Button-4>", lambda _e: canvas.yview_scroll(-1, "units"))
        self.bind_all("<Button-5>", lambda _e: canvas.yview_scroll(1, "units"))

    def _baue_header(self) -> None:
        header = tk.Frame(self, bg=_NAVY)
        header.pack(fill=tk.X)
        self._titel_label = tk.Label(
            header,
            text="Mein Studium – Dashboard",
            bg=_NAVY,
            fg="white",
            font=_FONT_TITEL,
            padx=18,
            pady=16,
        )
        self._titel_label.pack(side=tk.LEFT)
        self._ziele_label = tk.Label(
            header, text="", bg=_NAVY, fg="white", font=_FONT_KLEIN, padx=18
        )
        self._ziele_label.pack(side=tk.RIGHT)

    def _baue_kpi_zeile(self) -> None:
        zeile = tk.Frame(self._scroll_rahmen, bg=_HINTERGRUND)
        zeile.pack(fill=tk.X, padx=16, pady=(16, 10))
        for spalte in range(4):
            zeile.columnconfigure(spalte, weight=1, uniform="kpi")

        self._ects_card = self._erstelle_karte(zeile, "ECTS-Fortschritt", _CARD_BLAU, 0)
        self._noten_card = self._erstelle_karte(zeile, "Notendurchschnitt", _CARD_GELB, 1)
        self._pruefungs_card = self._erstelle_karte(zeile, "Prüfungsstatus", _CARD_ROT, 2)
        self._frist_card = self._erstelle_karte(zeile, "Nächste Frist", _CARD_GRAU, 3)

    def _erstelle_karte(
        self, eltern: tk.Widget, titel: str, farbe: str, spalte: int
    ) -> dict[str, tk.Label]:
        rahmen = tk.Frame(eltern, bg=farbe, highlightbackground="#dcdfe4", highlightthickness=1)
        rahmen.grid(row=0, column=spalte, sticky="nsew", padx=8, pady=2)
        tk.Label(rahmen, text=titel, bg=farbe, font=_FONT_UEBERSCHRIFT, anchor="center").pack(
            fill=tk.X, padx=12, pady=(12, 2)
        )
        wert_label = tk.Label(rahmen, text="–", bg=farbe, font=_FONT_WERT, anchor="center")
        wert_label.pack(fill=tk.X, padx=12)
        detail_label = tk.Label(
            rahmen, text="", bg=farbe, font=_FONT_KLEIN, anchor="center", justify=tk.CENTER
        )
        detail_label.pack(fill=tk.X, padx=12, pady=(0, 12))
        return {"wert": wert_label, "detail": detail_label}

    def _baue_mittlere_zeile(self) -> None:
        zeile = tk.Frame(self._scroll_rahmen, bg=_HINTERGRUND)
        zeile.pack(fill=tk.X, padx=16, pady=8)

        fortschritt_rahmen = tk.LabelFrame(
            zeile, text="Studienfortschritt und Soll/Ist-Abgleich", bg="white", padx=12, pady=12
        )
        fortschritt_rahmen.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        self._fortschrittsbalken = ttk.Progressbar(
            fortschritt_rahmen, orient="horizontal", mode="determinate", maximum=100
        )
        self._fortschrittsbalken.pack(fill=tk.X, pady=(0, 6))

        balken_beschriftung = tk.Frame(fortschritt_rahmen, bg="white")
        balken_beschriftung.pack(fill=tk.X)
        self._ist_label = tk.Label(balken_beschriftung, text="", bg="white", font=_FONT_KLEIN)
        self._ist_label.pack(side=tk.LEFT)
        self._ziel_label = tk.Label(balken_beschriftung, text="", bg="white", font=_FONT_KLEIN)
        self._ziel_label.pack(side=tk.RIGHT)

        ampel_rahmen = tk.LabelFrame(zeile, text="Zielampel", bg="white", padx=12, pady=12)
        ampel_rahmen.pack(side=tk.LEFT, fill=tk.BOTH, padx=(6, 0))

        for schluessel, beschriftung in (("ects", "ECTS"), ("noten", "Note"), ("fristen", "Frist")):
            badge = tk.Label(
                ampel_rahmen,
                text=beschriftung,
                font=_FONT_UEBERSCHRIFT,
                padx=12,
                pady=6,
                anchor="center",
            )
            badge.pack(fill=tk.X, pady=4)
            self._ampel_badges[schluessel] = (badge, beschriftung)

    def _baue_tabelle(self) -> None:
        rahmen = tk.LabelFrame(
            self._scroll_rahmen, text="Modul- und Prüfungsübersicht", bg="white", padx=10, pady=10
        )
        rahmen.pack(fill=tk.BOTH, expand=True, padx=14, pady=8)

        spalten = (
            "semester",
            "modul",
            "ects",
            "status",
            "pruefungsart",
            "pruefungsstatus",
            "datum",
            "punkte",
            "note",
        )
        beschriftungen = {
            "semester": "Semester",
            "modul": "Modul",
            "ects": "ECTS",
            "status": "Status",
            "pruefungsart": "Prüfung",
            "pruefungsstatus": "Prüfungsstatus",
            "datum": "Frist/Datum",
            "punkte": "Punkte",
            "note": "Note",
        }
        self._tabelle = ttk.Treeview(rahmen, columns=spalten, show="headings", height=8)
        for spalte in spalten:
            self._tabelle.heading(spalte, text=beschriftungen[spalte], anchor="center")
            self._tabelle.column(spalte, width=100, anchor="center")
        self._tabelle.pack(fill=tk.BOTH, expand=True)
        self._tabelle.bind("<<TreeviewSelect>>", self._auf_tabellenzeile_ausgewaehlt)

    def _baue_semester_bereich(self) -> None:
        """Eigener Bereich, um ein Semester zu löschen. Angelegt wird ein Semester

        nicht extra, sondern implizit über die Semesternummer beim Modul anlegen."""
        rahmen = tk.LabelFrame(
            self._scroll_rahmen, text="Semester löschen", bg="white", padx=12, pady=12
        )
        rahmen.pack(fill=tk.X, padx=14, pady=(8, 0))

        tk.Label(rahmen, text="Semesternummer:", bg="white").grid(row=0, column=0, sticky="w")
        self._semester_verwalten_eingabe = ttk.Entry(rahmen, width=8)
        self._semester_verwalten_eingabe.grid(row=0, column=1, padx=6, pady=4, sticky="w")

        loeschen_button = ttk.Button(
            rahmen, text="Semester löschen", command=self._auf_semester_loeschen_geklickt
        )
        loeschen_button.grid(row=0, column=2, padx=(12, 0), pady=4)

    def _baue_modul_anlegen_bereich(self) -> None:
        """Modul anlegen, bearbeiten und löschen: Titel und neuer Titel sind
        normale Textfelder zum Eintippen (kein Dropdown) – ganz ohne
        Prüfungsleistung. Existiert der Titel schon, aktualisiert 'Speichern'
        das bestehende Modul statt ein zweites anzulegen."""
        rahmen = tk.LabelFrame(
            self._scroll_rahmen,
            text="Modul anlegen / bearbeiten / löschen",
            bg="white",
            padx=12,
            pady=12,
        )
        rahmen.pack(fill=tk.X, padx=14, pady=(8, 0))

        tk.Label(rahmen, text="Modultitel:", bg="white").grid(row=0, column=0, sticky="w")
        self._neues_modul_titel_eingabe = ttk.Entry(rahmen, width=32)
        self._neues_modul_titel_eingabe.grid(row=0, column=1, padx=6, pady=4, sticky="w")

        tk.Label(rahmen, text="ECTS:", bg="white").grid(row=0, column=2, sticky="w")
        self._neues_modul_ects_eingabe = ttk.Entry(rahmen, width=6)
        self._neues_modul_ects_eingabe.insert(0, str(ECTS_VORSCHLAG))
        self._neues_modul_ects_eingabe.grid(row=0, column=3, padx=6, pady=4, sticky="w")

        tk.Label(rahmen, text="Semester:", bg="white").grid(row=0, column=4, sticky="w")
        self._neues_modul_semester_eingabe = ttk.Entry(rahmen, width=8)
        self._neues_modul_semester_eingabe.grid(row=0, column=5, padx=6, pady=4, sticky="w")

        tk.Label(rahmen, text="Status (optional):", bg="white").grid(row=0, column=6, sticky="w")
        self._neues_modul_status_auswahl = ttk.Combobox(
            rahmen,
            state="readonly",
            width=14,
            values=[status.value for status in ModulStatus],
        )
        self._neues_modul_status_auswahl.grid(row=0, column=7, padx=6, pady=4, sticky="w")

        tk.Label(rahmen, text="Neuer Titel (zum Umbenennen):", bg="white").grid(
            row=1, column=0, columnspan=2, sticky="w"
        )
        self._neuer_modultitel_eingabe = ttk.Entry(rahmen, width=32)
        self._neuer_modultitel_eingabe.grid(row=1, column=2, columnspan=2, padx=6, pady=4, sticky="w")

        speichern_button = ttk.Button(
            rahmen, text="Modul speichern", command=self._auf_modul_speichern_geklickt
        )
        speichern_button.grid(row=1, column=6, padx=(12, 6), pady=4, sticky="e")

        loeschen_button = ttk.Button(
            rahmen, text="Modul löschen", command=self._auf_modul_loeschen_geklickt
        )
        loeschen_button.grid(row=1, column=7, pady=4, sticky="e")

    def _baue_eingabebereich(self) -> None:
        rahmen = tk.LabelFrame(
            self._scroll_rahmen, text="Prüfungsleistung pflegen", bg="white", padx=12, pady=12
        )
        rahmen.pack(fill=tk.X, padx=14, pady=(0, 14))

        tk.Label(rahmen, text="Modultitel:", bg="white").grid(row=0, column=0, sticky="w")
        self._modultitel_auswahl = ttk.Combobox(rahmen, state="normal", width=25)
        self._modultitel_auswahl.grid(row=0, column=1, padx=6, pady=4, sticky="w")
        self._modultitel_auswahl.bind("<<ComboboxSelected>>", self._auf_modul_gewaehlt)
        self._modultitel_auswahl.bind("<FocusOut>", self._auf_modul_gewaehlt)

        tk.Label(rahmen, text="Prüfungstitel:", bg="white").grid(row=0, column=2, sticky="w")
        self._pruefungstitel_auswahl = ttk.Combobox(rahmen, state="normal", width=28)
        self._pruefungstitel_auswahl.grid(row=0, column=3, padx=6, pady=4, sticky="w")

        tk.Label(rahmen, text="Neuer Status:", bg="white").grid(row=1, column=0, sticky="w")
        self._status_auswahl = ttk.Combobox(
            rahmen,
            state="readonly",
            width=14,
            values=[status.value for status in PruefungsStatus],
        )
        self._status_auswahl.grid(row=1, column=1, padx=6, pady=4, sticky="w")

        tk.Label(rahmen, text="Neue Note:", bg="white").grid(row=1, column=2, sticky="w")
        self._note_eingabe = ttk.Entry(rahmen, width=10)
        self._note_eingabe.grid(row=1, column=3, padx=6, pady=4, sticky="w")

        tk.Label(rahmen, text="Neue Punkte:", bg="white").grid(row=2, column=0, sticky="w")
        self._punkte_eingabe = ttk.Entry(rahmen, width=14)
        self._punkte_eingabe.grid(row=2, column=1, padx=6, pady=4, sticky="w")

        tk.Label(rahmen, text="Neues Datum (JJJJ-MM-TT):", bg="white").grid(
            row=2, column=2, sticky="w"
        )
        self._datum_eingabe = ttk.Entry(rahmen, width=14)
        self._datum_eingabe.grid(row=2, column=3, padx=6, pady=4, sticky="w")

        tk.Label(rahmen, text="Prüfungsart (bei neuer Prüfung):", bg="white").grid(
            row=3, column=0, sticky="w"
        )
        self._pruefungsart_auswahl = ttk.Combobox(
            rahmen,
            state="readonly",
            width=25,
            values=[art.value for art in Pruefungsart],
        )
        self._pruefungsart_auswahl.grid(row=3, column=1, padx=6, pady=4, sticky="w")

        tk.Label(rahmen, text="Modulstatus (optional):", bg="white").grid(
            row=3, column=2, sticky="w"
        )
        self._modulstatus_auswahl = ttk.Combobox(
            rahmen,
            state="readonly",
            width=14,
            values=[status.value for status in ModulStatus],
        )
        self._modulstatus_auswahl.grid(row=3, column=3, padx=6, pady=4, sticky="w")

        tk.Label(rahmen, text="ECTS (bei neuem Modul):", bg="white").grid(
            row=4, column=0, sticky="w"
        )
        self._pruefung_ects_eingabe = ttk.Entry(rahmen, width=14)
        self._pruefung_ects_eingabe.grid(row=4, column=1, padx=6, pady=4, sticky="w")

        tk.Label(rahmen, text="Semester (bei neuem Modul):", bg="white").grid(
            row=4, column=2, sticky="w"
        )
        self._semester_eingabe = ttk.Entry(rahmen, width=25)
        self._semester_eingabe.grid(row=4, column=3, padx=6, pady=4, sticky="w")

        neu_laden_button = ttk.Button(rahmen, text="Neu laden", command=self.aktualisiere_ansicht)
        neu_laden_button.grid(row=5, column=1, sticky="w", pady=4)

        loeschen_button = ttk.Button(
            rahmen, text="Prüfung löschen", command=self._auf_pruefung_loeschen_geklickt
        )
        loeschen_button.grid(row=5, column=2, sticky="e", pady=4)

        aktualisieren_button = ttk.Button(
            rahmen, text="Speichern", command=self._auf_aktualisieren_geklickt
        )
        aktualisieren_button.grid(row=5, column=3, sticky="e", pady=4)

    # -- Datenanzeige ----------------------------------------------------------

    def aktualisiere_ansicht(self) -> None:
        """Lädt den Studenten neu von der Datei und aktualisiert alle Widgets."""
        self._render(self._controller.lade_neu())

    def _render(self, daten: DashboardDatenDTO) -> None:
        self._zeige_header(daten)
        self._zeige_kpi_karten(daten)
        self._zeige_fortschrittsbalken(daten)
        self._zeige_ampeln(daten)
        self._zeige_tabelle(daten)
        self._befuelle_modultitel_auswahl(daten)

    def _zeige_header(self, daten: DashboardDatenDTO) -> None:
        self._titel_label.config(text=f"{daten.student_name} – {daten.studiengang_name}")
        self._ziele_label.config(text=f"Ziel: {daten.ects_ziel} ECTS  |  Fristen im Blick")

    def _zeige_kpi_karten(self, daten: DashboardDatenDTO) -> None:
        self._ects_card["wert"].config(text=f"{daten.ects_ist} / {daten.ects_ziel}")
        self._ects_card["detail"].config(text=f"{daten.ects_fortschritt_prozent:.0f} % erreicht")

        notenschnitt_text = (
            f"{daten.notenschnitt:.2f}" if daten.notenschnitt is not None else "–"
        )
        self._noten_card["wert"].config(text=notenschnitt_text)
        self._noten_card["detail"].config(text="nur bewertete Leistungen")

        self._pruefungs_card["wert"].config(text=f"{daten.offene_pruefungen} offen")
        self._pruefungs_card["detail"].config(
            text=(
                f"{daten.angemeldete_pruefungen} davon angemeldet\n"
                f"Risiko: {daten.fristen_risiko_anzahl} Frist(en) knapp"
            )
        )

        if daten.naechster_termin is not None:
            self._frist_card["wert"].config(text=daten.naechster_termin.strftime("%d.%m."))
            self._frist_card["detail"].config(text=daten.naechste_pruefung_titel or "")
        else:
            self._frist_card["wert"].config(text="–")
            self._frist_card["detail"].config(text="keine offene Prüfung mit Datum")

    def _zeige_fortschrittsbalken(self, daten: DashboardDatenDTO) -> None:
        self._fortschrittsbalken["value"] = daten.ects_fortschritt_prozent
        self._ist_label.config(text=f"Ist: {daten.ects_ist} ECTS")
        self._ziel_label.config(text=f"Ziel: {daten.ects_ziel} ECTS")

    def _zeige_ampeln(self, daten: DashboardDatenDTO) -> None:
        zuordnung = {
            "ects": daten.zielampeln.ects,
            "noten": daten.zielampeln.noten,
            "fristen": daten.zielampeln.fristen,
        }
        for schluessel, ampel_status in zuordnung.items():
            hintergrund, vordergrund = _BADGE_FARBEN[ampel_status]
            badge, beschriftung = self._ampel_badges[schluessel]
            badge.config(
                bg=hintergrund,
                fg=vordergrund,
                text=f"{beschriftung}: {self._lesbar(ampel_status.value)}",
            )

    @staticmethod
    def _lesbar(enum_wert: str) -> str:
        """Formatiert einen Enum-Wert (z. B. 'nicht_bestanden') für die Anzeige
        als lesbaren, großgeschriebenen Text (z. B. 'Nicht bestanden')."""
        return enum_wert.replace("_", " ").capitalize()

    @staticmethod
    def _formatiere_punkte(punkte: float | None, max_punkte: float | None) -> str:
        """Zeigt 'Punkte/Maximalpunkte' (z. B. '73/100') an, wenn beide vorhanden
        sind, sonst nur die Punkte oder '-'."""
        if punkte is None:
            return "-"
        if max_punkte is not None:
            return f"{punkte:.0f}/{max_punkte:.0f}"
        return f"{punkte:.0f}"

    def _zeige_tabelle(self, daten: DashboardDatenDTO) -> None:
        self._tabelle.delete(*self._tabelle.get_children())
        self._pruefungstitel_by_modultitel.clear()
        self._modul_info_by_titel.clear()

        for eintrag in daten.module:
            modul = eintrag.modul
            self._pruefungstitel_by_modultitel[modul.titel] = [
                p.titel for p in modul.pruefungsleistungen
            ]
            self._modul_info_by_titel[modul.titel] = (modul.ects, modul.status)

            if not modul.pruefungsleistungen:
                self._tabelle.insert(
                    "",
                    tk.END,
                    values=(
                        eintrag.semester_nummer,
                        modul.titel,
                        modul.ects,
                        self._lesbar(modul.status.value),
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                    ),
                )
                continue

            for pruefungsleistung in modul.pruefungsleistungen:
                datum_text = (
                    pruefungsleistung.relevantes_datum.isoformat()
                    if pruefungsleistung.relevantes_datum
                    else "-"
                )
                note_text = (
                    f"{pruefungsleistung.note:.2f}" if pruefungsleistung.note is not None else "-"
                )
                punkte_text = self._formatiere_punkte(
                    pruefungsleistung.punkte, pruefungsleistung.max_punkte
                )
                self._tabelle.insert(
                    "",
                    tk.END,
                    values=(
                        eintrag.semester_nummer,
                        modul.titel,
                        modul.ects,
                        self._lesbar(modul.status.value),
                        self._lesbar(pruefungsleistung.art.value),
                        self._lesbar(pruefungsleistung.status.value),
                        datum_text,
                        punkte_text,
                        note_text,
                    ),
                )

    def _befuelle_modultitel_auswahl(self, daten: DashboardDatenDTO) -> None:
        modultitel = [eintrag.modul.titel for eintrag in daten.module]
        self._modultitel_auswahl["values"] = modultitel

    # -- Eingabeverarbeitung -------------------------------------------------

    def _auf_tabellenzeile_ausgewaehlt(self, _ereignis: object) -> None:
        auswahl = self._tabelle.selection()
        if not auswahl:
            return
        werte = self._tabelle.item(auswahl[0], "values")
        modultitel = str(werte[1])
        if modultitel in self._modultitel_auswahl["values"]:
            self._modultitel_auswahl.set(modultitel)
            self._befuelle_pruefungstitel_auswahl(modultitel)

        modul_info = self._modul_info_by_titel.get(modultitel)
        if modul_info is not None:
            ects, status = modul_info
            self._neues_modul_titel_eingabe.delete(0, tk.END)
            self._neues_modul_titel_eingabe.insert(0, modultitel)
            self._neues_modul_ects_eingabe.delete(0, tk.END)
            self._neues_modul_ects_eingabe.insert(0, str(ects))
            self._neues_modul_status_auswahl.set(status.value)
            self._neuer_modultitel_eingabe.delete(0, tk.END)

    def _auf_modul_gewaehlt(self, _ereignis: object) -> None:
        self._befuelle_pruefungstitel_auswahl(self._modultitel_auswahl.get())

    def _befuelle_pruefungstitel_auswahl(self, modultitel: str) -> None:
        titel_liste = self._pruefungstitel_by_modultitel.get(modultitel, [])
        self._pruefungstitel_auswahl["values"] = titel_liste
        if titel_liste and not self._pruefungstitel_auswahl.get().strip():
            self._pruefungstitel_auswahl.set(titel_liste[0])

    def _auf_modul_speichern_geklickt(self) -> None:
        titel = self._neues_modul_titel_eingabe.get().strip()
        if not titel:
            messagebox.showerror("Eingabe fehlt", "Bitte einen Modultitel eingeben.")
            return

        ects_text = self._neues_modul_ects_eingabe.get().strip()
        try:
            ects = int(ects_text)
            if ects <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Ungültige ECTS", "Bitte eine positive Ganzzahl als ECTS eingeben."
            )
            return

        semester_text = self._neues_modul_semester_eingabe.get().strip()
        semester_nummer: int | None = None
        if semester_text:
            try:
                semester_nummer = int(semester_text)
            except ValueError:
                messagebox.showerror(
                    "Ungültiges Semester", "Bitte eine Ganzzahl als Semester eingeben."
                )
                return

        status_text = self._neues_modul_status_auswahl.get().strip()
        status = ModulStatus(status_text) if status_text else None

        neuer_titel = self._neuer_modultitel_eingabe.get().strip() or None

        eingabe = ModulAnlageDTO(
            titel=titel,
            ects=ects,
            semester_nummer=semester_nummer,
            status=status,
            neuer_titel=neuer_titel,
        )
        try:
            daten = self._controller.lege_modul_an(eingabe)
        except ModulNichtGefundenError as fehler:
            messagebox.showerror(
                "Modul nicht gefunden", f"{fehler}\n\nBitte ein Semester angeben, um es neu anzulegen."
            )
            return
        except ModulBereitsVorhandenError as fehler:
            messagebox.showerror("Titel bereits vergeben", str(fehler))
            return

        self._neues_modul_titel_eingabe.delete(0, tk.END)
        self._neues_modul_ects_eingabe.delete(0, tk.END)
        self._neues_modul_ects_eingabe.insert(0, str(ECTS_VORSCHLAG))
        self._neues_modul_semester_eingabe.delete(0, tk.END)
        self._neues_modul_status_auswahl.set("")
        self._neuer_modultitel_eingabe.delete(0, tk.END)
        self._render(daten)

    def _auf_modul_loeschen_geklickt(self) -> None:
        titel = self._neues_modul_titel_eingabe.get().strip()
        if not titel:
            messagebox.showerror("Eingabe fehlt", "Bitte den Titel des zu löschenden Moduls eingeben.")
            return

        if not messagebox.askyesno(
            "Modul löschen",
            f"Modul '{titel}' inklusive aller enthaltenen Prüfungsleistungen wirklich löschen?",
        ):
            return

        try:
            daten = self._controller.loesche_modul(titel)
        except ModulNichtGefundenError as fehler:
            messagebox.showerror("Modul nicht gefunden", str(fehler))
            return

        self._neues_modul_titel_eingabe.delete(0, tk.END)
        self._neues_modul_ects_eingabe.delete(0, tk.END)
        self._neues_modul_ects_eingabe.insert(0, str(ECTS_VORSCHLAG))
        self._neues_modul_semester_eingabe.delete(0, tk.END)
        self._neues_modul_status_auswahl.set("")
        self._neuer_modultitel_eingabe.delete(0, tk.END)
        self._render(daten)

    def _auf_semester_loeschen_geklickt(self) -> None:
        semester_text = self._semester_verwalten_eingabe.get().strip()
        try:
            nummer = int(semester_text)
        except ValueError:
            messagebox.showerror(
                "Ungültiges Semester", "Bitte eine Ganzzahl als Semesternummer eingeben."
            )
            return

        if not messagebox.askyesno(
            "Semester löschen",
            f"Semester {nummer} inklusive aller enthaltenen Module und Prüfungsleistungen "
            "wirklich löschen?",
        ):
            return

        try:
            daten = self._controller.loesche_semester(nummer)
        except SemesterNichtGefundenError as fehler:
            messagebox.showerror("Semester nicht gefunden", str(fehler))
            return

        self._semester_verwalten_eingabe.delete(0, tk.END)
        self._render(daten)

    def _auf_aktualisieren_geklickt(self) -> None:
        modultitel = self._modultitel_auswahl.get().strip()
        pruefungstitel = self._pruefungstitel_auswahl.get().strip()
        if not modultitel or not pruefungstitel:
            messagebox.showerror("Eingabe fehlt", "Bitte Modul und Prüfungstitel auswählen.")
            return

        status_text = self._status_auswahl.get().strip()
        status = PruefungsStatus(status_text) if status_text else None

        note_text = self._note_eingabe.get().strip()
        note: float | None = None
        if note_text:
            try:
                note = float(note_text.replace(",", "."))
            except ValueError:
                messagebox.showerror("Ungültige Note", "Bitte eine Zahl als Note eingeben.")
                return
            if not (NOTE_MIN <= note <= NOTE_MAX):
                messagebox.showerror(
                    "Ungültige Note",
                    f"Die Note muss zwischen {NOTE_MIN:.1f} und {NOTE_MAX:.1f} liegen.",
                )
                return

        punkte_text = self._punkte_eingabe.get().strip()
        punkte: float | None = None
        if punkte_text:
            try:
                punkte = float(punkte_text.replace(",", "."))
            except ValueError:
                messagebox.showerror("Ungültige Punkte", "Bitte eine Zahl als Punkte eingeben.")
                return
            if punkte < 0:
                messagebox.showerror("Ungültige Punkte", "Punkte dürfen nicht negativ sein.")
                return

        datum_text = self._datum_eingabe.get().strip()
        relevantes_datum: date | None = None
        if datum_text:
            try:
                relevantes_datum = date.fromisoformat(datum_text)
            except ValueError:
                messagebox.showerror(
                    "Ungültiges Datum", "Bitte Datum im Format JJJJ-MM-TT eingeben."
                )
                return

        art_text = self._pruefungsart_auswahl.get().strip()
        art = Pruefungsart(art_text) if art_text else None

        modulstatus_text = self._modulstatus_auswahl.get().strip()
        modul_status = ModulStatus(modulstatus_text) if modulstatus_text else None

        ects_text = self._pruefung_ects_eingabe.get().strip()
        ects: int | None = None
        if ects_text:
            try:
                ects = int(ects_text)
                if ects <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Ungültige ECTS", "Bitte eine positive Ganzzahl als ECTS eingeben."
                )
                return

        semester_text = self._semester_eingabe.get().strip()
        semester_nummer: int | None = None
        if semester_text:
            try:
                semester_nummer = int(semester_text)
            except ValueError:
                messagebox.showerror(
                    "Ungültiges Semester", "Bitte eine Ganzzahl als Semester eingeben."
                )
                return

        update = PruefungsUpdateDTO(
            modultitel=modultitel,
            pruefungstitel=pruefungstitel,
            status=status,
            note=note,
            punkte=punkte,
            relevantes_datum=relevantes_datum,
            art=art,
            modul_status=modul_status,
            ects=ects,
            semester_nummer=semester_nummer,
        )
        try:
            daten = self._controller.aktualisiere_pruefung(update)
        except ModulNichtGefundenError as fehler:
            messagebox.showerror(
                "Modul nicht gefunden",
                f"{fehler}\n\nBitte Modultitel und Semester ausfüllen, um es neu "
                "anzulegen.",
            )
            return
        except PruefungsleistungNichtGefundenError as fehler:
            messagebox.showerror(
                "Prüfungsleistung nicht gefunden",
                f"{fehler}\n\nBitte eine Prüfungsart auswählen, um sie neu anzulegen.",
            )
            return

        self._note_eingabe.delete(0, tk.END)
        self._punkte_eingabe.delete(0, tk.END)
        self._datum_eingabe.delete(0, tk.END)
        self._pruefungsart_auswahl.set("")
        self._modulstatus_auswahl.set("")
        self._pruefung_ects_eingabe.delete(0, tk.END)
        self._semester_eingabe.delete(0, tk.END)
        self._render(daten)

    def _auf_pruefung_loeschen_geklickt(self) -> None:
        modultitel = self._modultitel_auswahl.get().strip()
        pruefungstitel = self._pruefungstitel_auswahl.get().strip()
        if not modultitel or not pruefungstitel:
            messagebox.showerror("Eingabe fehlt", "Bitte Modul und Prüfungstitel auswählen.")
            return

        if not messagebox.askyesno(
            "Prüfung löschen",
            f"Prüfungsleistung '{pruefungstitel}' aus Modul '{modultitel}' wirklich löschen?",
        ):
            return

        try:
            daten = self._controller.loesche_pruefungsleistung(modultitel, pruefungstitel)
        except ModulNichtGefundenError as fehler:
            messagebox.showerror("Modul nicht gefunden", str(fehler))
            return
        except PruefungsleistungNichtGefundenError as fehler:
            messagebox.showerror("Prüfungsleistung nicht gefunden", str(fehler))
            return

        self._pruefungstitel_auswahl.set("")
        self._render(daten)

    def _auf_csv_importieren_geklickt(self) -> None:
        datei_pfad = filedialog.askopenfilename(
            title="CSV-Datei auswählen",
            filetypes=[("CSV-Dateien", "*.csv"), ("Alle Dateien", "*.*")],
        )
        if not datei_pfad:
            return

        try:
            daten = self._controller.importiere_csv(Path(datei_pfad))
        except CsvImportError as fehler:
            messagebox.showerror("CSV-Import fehlgeschlagen", str(fehler))
            return

        self._render(daten)
        messagebox.showinfo(
            "CSV-Import erfolgreich",
            "Die CSV-Datei wurde eingelesen. Modulübersicht, ECTS-Fortschritt, "
            "Notendurchschnitt und Zielampel wurden aktualisiert.",
        )

    def _auf_dashboard_zuruecksetzen_geklickt(self) -> None:
        if not messagebox.askyesno(
            "Dashboard zurücksetzen",
            "Wirklich ALLE Semester, Module und Prüfungsleistungen unwiderruflich "
            "löschen?\n\nDie Studienziele (ECTS-, Noten- und Fristenziel) bleiben "
            "erhalten. Diese Aktion kann nicht rückgängig gemacht werden.",
            icon="warning",
        ):
            return

        daten = self._controller.setze_dashboard_zurueck()
        self._render(daten)
