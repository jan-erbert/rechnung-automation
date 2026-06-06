import argparse
import os
from pathlib import Path

from dotenv import set_key

ENV_KEYS = ("MAIL_SERVER", "MAIL_PORT", "MAIL_USER", "MAIL_PASS")


def schreibe_mail_env(pfad: Path, values: dict[str, str]) -> None:
    """Schreibt SMTP-Werte sicher in eine lokale Env-Datei."""
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.touch(mode=0o600, exist_ok=True)
    pfad.chmod(0o600)
    for key in ENV_KEYS:
        set_key(pfad, key, values[key], quote_mode="always")


def main() -> None:
    """Schreibt die Mail-Konfiguration aus MAIL_-Umgebungsvariablen."""
    parser = argparse.ArgumentParser()
    parser.add_argument("env_path", type=Path)
    args = parser.parse_args()
    values = {key: os.environ[key] for key in ENV_KEYS}
    schreibe_mail_env(args.env_path, values)


if __name__ == "__main__":
    main()
