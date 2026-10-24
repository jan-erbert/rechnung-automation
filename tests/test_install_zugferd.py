"""Prueft das optionale Setup ohne Downloads oder Paketinstallationen."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "install_zugferd.py"
SPEC = importlib.util.spec_from_file_location("install_zugferd", SCRIPT)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


def test_pinned_optional_requirements():
    """Alle optionalen Abhaengigkeiten haben feste Versionen."""
    versions = installer.required_versions()
    assert versions == {
        "drafthorse": "2025.2.0",
        "lxml": "6.1.3",
        "pypdf": "6.21.2",
        "saxonche": "13.1.0",
    }


def test_check_reports_missing_and_wrong_version(monkeypatch):
    """Fehlende und abweichende Pakete werden sichtbar gemeldet."""

    def version(name):
        """Simuliert installierte Metadaten ohne Paketzugriff."""
        if name == "missing":
            raise installer.metadata.PackageNotFoundError(name)
        return "1.0"

    monkeypatch.setattr(installer.metadata, "version", version)
    errors = installer.check_versions({"missing": "2.0", "wrong": "2.0"})
    assert len(errors) == 2
    assert "fehlt" in errors[0]
    assert "installiert 1.0" in errors[1]


def test_default_check_never_installs(monkeypatch):
    """Ohne ausdruecklichen Schalter gibt es keinen pip-Aufruf."""

    def forbid(*args, **kwargs):
        """Verhindert unangeforderte Unterprozesse."""
        raise AssertionError("Kein Installationsprozess erlaubt")

    monkeypatch.setattr(installer.subprocess, "run", forbid)
    monkeypatch.setattr(installer, "check_versions", lambda versions: [])
    monkeypatch.setattr(installer, "check_imports", lambda: [])
    monkeypatch.setattr(installer, "check_rules", lambda: [])
    assert installer.main([]) == 0


def test_explicit_install_uses_current_python_and_wheels(monkeypatch):
    """Installation bleibt im gewaehlten Interpreter und baut keinen Quellcode."""
    calls = []

    def run(command, **kwargs):
        """Erfasst den Aufruf, ohne einen Prozess zu starten."""
        calls.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(installer.subprocess, "run", run)
    monkeypatch.setattr(installer, "check_versions", lambda versions: [])
    monkeypatch.setattr(installer, "check_imports", lambda: [])
    monkeypatch.setattr(installer, "check_rules", lambda: [])
    assert installer.main(["--install"]) == 0
    assert calls[0][0] == installer.sys.executable
    assert "--only-binary=:all:" in calls[0]
    assert str(installer.REQUIREMENTS) in calls[0]


def test_failed_pip_stops_before_import_checks(monkeypatch):
    """Ein fehlgeschlagener Installationsprozess wird nicht als Erfolg gemeldet."""
    monkeypatch.setattr(
        installer.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1),
    )
    assert installer.main(["--install"]) == 1


def test_native_import_failure_is_reported(monkeypatch):
    """Nicht ladbare native Bibliotheken erhalten einen Setupfehler."""

    def import_module(name):
        """Simuliert einen nativen Bibliotheksfehler."""
        if name == "saxonche":
            raise OSError("native library missing")

    monkeypatch.setattr(installer.importlib, "import_module", import_module)
    assert installer.check_imports() == [
        "saxonche kann nicht geladen werden: native library missing"
    ]
