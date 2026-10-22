"""Uebersetzt optionale Windmill-Ressourcen in die gemeinsame SMTP-Konfiguration."""

from collections.abc import Callable, Mapping

from openbao_secrets import read_kv2_secret


def _load_resource(path: str) -> dict:
    """Laedt den Windmill-Client erst innerhalb der optionalen Integration."""
    try:
        import wmill
    except ImportError:
        raise RuntimeError(
            "Die Windmill-Integration benoetigt den optionalen Windmill-Client."
        ) from None
    try:
        return wmill.get_resource(path)
    except Exception:
        raise RuntimeError("Windmill-Ressource konnte nicht geladen werden.") from None


def _required_text(config: Mapping, key: str) -> str:
    """Prueft ein SMTP-Feld ohne Zugangsdaten in die Fehlermeldung zu uebernehmen."""
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("SMTP-Ressource ist unvollstaendig.")
    return value


def _integer(value, maximum: int) -> int:
    """Prueft positive ganzzahlige Verbindungswerte ohne vertrauliche Ausgabe."""
    if isinstance(value, bool):
        raise ValueError("SMTP-Ressource enthaelt einen ungueltigen Zahlenwert.")
    if not isinstance(value, (int, str)):
        raise ValueError("SMTP-Ressource enthaelt einen ungueltigen Zahlenwert.")
    try:
        number = int(value)
    except ValueError:
        raise ValueError(
            "SMTP-Ressource enthaelt einen ungueltigen Zahlenwert."
        ) from None
    if not 0 < number <= maximum:
        raise ValueError("SMTP-Ressource enthaelt einen ungueltigen Zahlenwert.")
    return number


def load_smtp_resource(path: str, resource_loader: Callable | None = None) -> dict:
    """Loest SMTP-Zugangsdaten im Prozess auf und liefert die gemeinsame Mailconfig."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("SMTP-Ressourcenpfad fehlt.")
    loader = resource_loader or _load_resource
    config = loader(path)
    if not isinstance(config, Mapping):
        raise ValueError("SMTP-Ressource muss ein Objekt sein.")
    server = _required_text(config, "server")
    port = _integer(config.get("port"), 65535)
    security = config.get("security", "starttls")
    if not isinstance(security, str) or security not in {"starttls", "ssl"}:
        raise ValueError("SMTP-Sicherheit muss starttls oder ssl sein.")
    timeout = _integer(config.get("timeout", 30), 3600)
    provider = config.get("secret_provider", "windmill")
    if provider == "openbao":
        vault = loader(_required_text(config, "openbao_resource"))
        credentials = read_kv2_secret(vault)
    elif provider == "windmill":
        credentials = config
    else:
        raise ValueError("Unbekannter SMTP-Secret-Provider.")
    return {
        "server": server,
        "port": port,
        "user": _required_text(credentials, "user"),
        "password": _required_text(credentials, "password"),
        "security": security,
        "timeout": timeout,
    }
