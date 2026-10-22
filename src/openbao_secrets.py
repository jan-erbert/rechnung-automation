"""Liest einen freigegebenen KV-v2-Datensatz ueber eine eigene AppRole."""

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping


class OpenBaoError(RuntimeError):
    """Kennzeichnet einen Secret-Abruf ohne vertrauliche Fehlerdetails."""


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    """Verhindert die Weitergabe von Anmeldedaten an Weiterleitungsziele."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Lehnt jede HTTP-Weiterleitung fuer Secret-Aufrufe ab."""
        return None


def _text(config: Mapping, key: str) -> str:
    """Prueft ein erforderliches Textfeld ohne dessen Inhalt auszugeben."""
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        raise OpenBaoError("OpenBao-Konfiguration ist unvollstaendig.")
    return value


def _path(value: str) -> str:
    """Kodiert einen relativen API-Pfad ohne leere oder aufsteigende Segmente."""
    if not isinstance(value, str) or not value.strip():
        raise OpenBaoError("OpenBao-Konfiguration enthaelt einen ungueltigen Pfad.")
    parts = value.split("/")
    if any(not part or part in {".", ".."} for part in parts):
        raise OpenBaoError("OpenBao-Konfiguration enthaelt einen ungueltigen Pfad.")
    return "/".join(urllib.parse.quote(part, safe="") for part in parts)


def _url(value: str) -> str:
    """Akzeptiert ausschliesslich HTTPS ohne Zugangsdaten oder URL-Parameter."""
    try:
        parsed = urllib.parse.urlsplit(value)
        valid = (
            parsed.scheme == "https"
            and parsed.hostname
            and parsed.username is None
            and parsed.password is None
            and not parsed.query
            and not parsed.fragment
            and not any(c.isspace() for c in value)
        )
        parsed.port
    except ValueError:
        valid = False
    if not valid:
        raise OpenBaoError("OpenBao benoetigt eine gueltige HTTPS-Adresse.")
    if parsed.path.strip("/"):
        _path(parsed.path.strip("/"))
    return value.rstrip("/")


def _request(opener, base, path, timeout, payload=None, token=None):
    """Sendet eine HTTPS-Anfrage und unterdrueckt vertrauliche Antwortdetails."""
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["X-Vault-Token"] = token
    try:
        request = urllib.request.Request(
            base + "/v1/" + path,
            headers=headers,
            method="POST" if payload is not None else "GET",
            data=None if payload is None else json.dumps(payload).encode("utf-8"),
        )
        with opener.open(request, timeout=timeout) as response:
            raw = response.read(1_048_577)
        if len(raw) > 1_048_576:
            raise OpenBaoError("OpenBao-Antwort ist zu gross.")
        if not raw:
            return {}
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError
        return result
    except urllib.error.HTTPError as error:
        error.close()
        raise OpenBaoError(f"OpenBao-Anfrage abgewiesen (HTTP {error.code}).") from None
    except (urllib.error.URLError, OSError, ValueError):
        raise OpenBaoError("OpenBao-Anfrage fehlgeschlagen.") from None


def read_kv2_secret(config: Mapping) -> dict:
    """Liest genau einen KV-v2-Pfad und widerruft den kurzlebigen Sitzungstoken."""
    if not isinstance(config, Mapping):
        raise OpenBaoError("OpenBao-Konfiguration muss ein Objekt sein.")
    base = _url(_text(config, "url"))
    mount = _path(_text(config, "mount"))
    path = _path(_text(config, "path"))
    auth_mount = _path(config.get("auth_mount", "approle"))
    role_id = _text(config, "role_id")
    secret_id = _text(config, "secret_id")
    timeout = config.get("timeout", 10)
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not 0 < timeout <= 60
    ):
        raise OpenBaoError("OpenBao-Timeout muss zwischen 0 und 60 Sekunden liegen.")
    opener = urllib.request.build_opener(_RejectRedirects())
    token = None
    failed = False
    try:
        login = _request(
            opener,
            base,
            f"auth/{auth_mount}/login",
            timeout,
            payload={"role_id": role_id, "secret_id": secret_id},
        )
        auth = login.get("auth")
        if (
            not isinstance(auth, dict)
            or not isinstance(auth.get("client_token"), str)
            or not auth["client_token"]
        ):
            raise OpenBaoError("OpenBao-Anmeldung lieferte keinen Sitzungstoken.")
        token = auth["client_token"]
        lease = auth.get("lease_duration")
        if (
            isinstance(lease, bool)
            or not isinstance(lease, int)
            or not 0 < lease <= 300
        ):
            raise OpenBaoError("OpenBao-Sitzung muss hoechstens fuenf Minuten gelten.")
        response = _request(opener, base, f"{mount}/data/{path}", timeout, token=token)
        data = response.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("data"), dict):
            raise OpenBaoError("OpenBao lieferte keinen gueltigen KV-v2-Datensatz.")
        return dict(data["data"])
    except BaseException:
        failed = True
        raise
    finally:
        if token:
            try:
                _request(
                    opener,
                    base,
                    "auth/token/revoke-self",
                    timeout,
                    payload={},
                    token=token,
                )
            except OpenBaoError:
                message = "OpenBao-Sitzung konnte nicht widerrufen werden."
                if failed:
                    message = (
                        "OpenBao-Abruf fehlgeschlagen; "
                        "Sitzung konnte nicht widerrufen werden."
                    )
                raise OpenBaoError(message) from None
