"""Installiert oder prueft die ausdruecklich optionalen ZUGFeRD-Pakete."""

import argparse
import importlib
from importlib import metadata
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = PROJECT_ROOT / "install" / "requirements-zugferd.txt"


def required_versions(path: Path = REQUIREMENTS) -> dict[str, str]:
    """Liest die festgelegten optionalen Paketversionen ohne Projektkonfiguration."""
    versions = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, version = line.split("==", 1)
        versions[name] = version
    return versions


def check_versions(versions: dict[str, str]) -> list[str]:
    """Meldet fehlende oder abweichende optionale Pakete."""
    errors = []
    for name, expected in versions.items():
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            errors.append(f"{name} fehlt (benoetigt: {expected}).")
            continue
        if installed != expected:
            errors.append(f"{name}: erwartet {expected}, installiert {installed}.")
    return errors


def check_imports() -> list[str]:
    """Prueft native Erweiterungen ohne Rechnungsdaten oder PDF-Erzeugung."""
    errors = []
    for name in ("drafthorse", "lxml.etree", "pypdf", "saxonche"):
        try:
            importlib.import_module(name)
        except (ImportError, OSError) as exc:
            errors.append(f"{name} kann nicht geladen werden: {exc}")
    return errors


def check_rules() -> list[str]:
    """Prueft das lokale Regelpaket ohne Download oder Rechnungserzeugung."""
    src_dir = str(PROJECT_ROOT / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    try:
        from zugferd_validation import check_validation_setup

        check_validation_setup()
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        return [f"Lokale ZUGFeRD-Pruefregeln nicht bereit: {exc}"]
    return []


def main(argv: list[str] | None = None) -> int:
    """Installiert nur auf explizite Anforderung und startet keine Rechnung."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--install",
        action="store_true",
        help="Optionale Pakete mit pip in die aktuelle Python-Umgebung installieren",
    )
    args = parser.parse_args(argv)
    if args.install:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--only-binary=:all:",
                "-r",
                str(REQUIREMENTS),
            ],
            check=False,
        )
        if result.returncode:
            print(
                "Optionale Installation fehlgeschlagen. Es werden passende Wheels "
                "fuer Betriebssystem, Architektur und Python benoetigt; "
                "kein automatischer Quellcode-Build. Siehe README.",
                file=sys.stderr,
            )
            return 1
    errors = check_versions(required_versions())
    if not errors:
        errors.extend(check_imports())
    if not errors:
        errors.extend(check_rules())
    if errors:
        print("\n".join(errors), file=sys.stderr)
        print(
            "Optionale Installation: python tools/install_zugferd.py --install",
            file=sys.stderr,
        )
        return 1
    print("Optionale ZUGFeRD-Pakete vorhanden; keine Rechnung ausgefuehrt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
