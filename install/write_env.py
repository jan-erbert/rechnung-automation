import argparse
import os
from pathlib import Path

from dotenv import set_key

ENV_KEYS = ("MAIL_SERVER", "MAIL_PORT", "MAIL_USER", "MAIL_PASS")


def write_mail_env(path: Path, values: dict[str, str]) -> None:
    """Schreibt SMTP-Werte sicher in eine lokale Env-Datei."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)
    for key in ENV_KEYS:
        set_key(path, key, values[key], quote_mode="always")


def main() -> None:
    """Schreibt die Mail-Konfiguration aus MAIL_-Umgebungsvariablen."""
    parser = argparse.ArgumentParser()
    parser.add_argument("env_path", type=Path)
    args = parser.parse_args()
    values = {key: os.environ[key] for key in ENV_KEYS}
    write_mail_env(args.env_path, values)


if __name__ == "__main__":
    main()
