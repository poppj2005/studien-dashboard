"""Fachliche Ausnahmen der Domain-Schicht."""


class ModulNichtGefundenError(Exception):
    """Wird ausgelöst, wenn zu einem Modultitel kein Modul existiert."""


class PruefungsleistungNichtGefundenError(Exception):
    """Wird ausgelöst, wenn ein Modul keine Prüfungsleistung mit dem gesuchten Titel hat."""


class SemesterNichtGefundenError(Exception):
    """Wird ausgelöst, wenn zu einer Semesternummer kein Semester existiert."""


class ModulBereitsVorhandenError(Exception):
    """Wird ausgelöst, wenn ein Modul beim Umbenennen auf einen bereits vergebenen Titel stößt."""


class CsvImportError(Exception):
    """Wird ausgelöst, wenn eine CSV-Datei fehlende Spalten oder ungültige Werte enthält.

    Die Fehlermeldung ist bereits für die Anzeige in der GUI aufbereitet
    (menschenlesbar, ggf. mit mehreren Zeilen für mehrere Fehler).
    """
