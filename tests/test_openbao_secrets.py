"""Prueft Secret-Abrufe nur mit erfundenen Daten und simulierten HTTPS-Antworten."""

import io
import json
import urllib.error
from unittest.mock import Mock

import pytest

import openbao_secrets
from openbao_secrets import OpenBaoError, read_kv2_secret


@pytest.fixture
def config():
    """Liefert eine vollstaendig erfundene AppRole-Konfiguration."""
    return {
        "url": "https://vault.example.invalid",
        "mount": "projects",
        "path": "invoices/smtp",
        "role_id": "fixture-role",
        "secret_id": "fixture-login-secret",
    }


def response(data):
    """Simuliert eine geschlossene JSON-Antwort ohne Netzwerkverbindung."""
    return io.BytesIO(json.dumps(data).encode())


def login(lease=120):
    """Erstellt eine kurzlebige erfundene OpenBao-Sitzung."""
    return response(
        {"auth": {"client_token": "fixture-session-token", "lease_duration": lease}}
    )


def opener_with(monkeypatch, answers):
    """Ersetzt den kompletten HTTPS-Opener und zeichnet nur Testanfragen auf."""
    opener = Mock()
    opener.open.side_effect = answers
    build = Mock(return_value=opener)
    monkeypatch.setattr(openbao_secrets.urllib.request, "build_opener", build)
    return opener, build


def test_reads_exact_kv2_path_and_revokes_session(monkeypatch, config):
    """Sendet Login, begrenzten Lesezugriff und Widerruf in dieser Reihenfolge."""
    opener, build = opener_with(
        monkeypatch,
        [
            login(),
            response({"data": {"data": {"password": "fixture-password"}}}),
            response({}),
        ],
    )

    result = read_kv2_secret(config)

    assert result == {"password": "fixture-password"}
    requests = [call.args[0] for call in opener.open.call_args_list]
    assert [request.full_url for request in requests] == [
        "https://vault.example.invalid/v1/auth/approle/login",
        "https://vault.example.invalid/v1/projects/data/invoices/smtp",
        "https://vault.example.invalid/v1/auth/token/revoke-self",
    ]
    assert [request.method for request in requests] == ["POST", "GET", "POST"]
    assert json.loads(requests[0].data) == {
        "role_id": "fixture-role",
        "secret_id": "fixture-login-secret",
    }
    assert requests[0].get_header("X-vault-token") is None
    assert requests[1].get_header("X-vault-token") == "fixture-session-token"
    assert isinstance(build.call_args.args[0], openbao_secrets._RejectRedirects)
    assert all(call.kwargs["timeout"] == 10 for call in opener.open.call_args_list)


def test_read_failure_is_redacted_and_still_revokes(monkeypatch, config):
    """Ein fehlgeschlagener Read gibt keine Antwortdetails oder Secrets aus."""
    error = urllib.error.HTTPError(
        "https://fixture.invalid",
        403,
        "fixture-password",
        {},
        io.BytesIO(b"fixture-password"),
    )
    opener, _ = opener_with(monkeypatch, [login(), error, response({})])

    with pytest.raises(OpenBaoError) as caught:
        read_kv2_secret(config)

    assert str(caught.value) == "OpenBao-Anfrage abgewiesen (HTTP 403)."
    assert "fixture-password" not in str(caught.value)
    assert opener.open.call_count == 3
    assert opener.open.call_args.args[0].full_url.endswith("auth/token/revoke-self")


def test_connection_failure_is_redacted(monkeypatch, config):
    """Unterdrueckt Netzwerkfehlerdetails und startet ohne Sitzung keinen Widerruf."""
    opener, _ = opener_with(
        monkeypatch, [urllib.error.URLError("fixture-login-secret")]
    )

    with pytest.raises(OpenBaoError, match="OpenBao-Anfrage fehlgeschlagen"):
        read_kv2_secret(config)

    assert opener.open.call_count == 1


def test_malformed_kv_response_still_revokes(monkeypatch, config):
    """Verwirft eine falsche Secret-Struktur und gibt die Sitzung frei."""
    opener, _ = opener_with(
        monkeypatch, [login(), response({"data": []}), response({})]
    )

    with pytest.raises(OpenBaoError, match="KV-v2-Datensatz"):
        read_kv2_secret(config)

    assert opener.open.call_count == 3


def test_revoke_failure_is_reported(monkeypatch, config):
    """Ein gelesener Wert wird bei fehlgeschlagenem Widerruf nicht weitergegeben."""
    opener_with(
        monkeypatch,
        [
            login(),
            response({"data": {"data": {}}}),
            urllib.error.URLError("fixture-token"),
        ],
    )

    with pytest.raises(OpenBaoError, match="Sitzung konnte nicht widerrufen"):
        read_kv2_secret(config)


@pytest.mark.parametrize("lease", [0, 301, 3600, None, True])
def test_refuses_long_lived_or_invalid_session(monkeypatch, config, lease):
    """Lehnt eine unpassend konfigurierte AppRole ab und widerruft deren Token."""
    opener, _ = opener_with(monkeypatch, [login(lease), response({})])

    with pytest.raises(OpenBaoError, match="hoechstens fuenf Minuten"):
        read_kv2_secret(config)

    assert opener.open.call_count == 2
    assert opener.open.call_args.args[0].full_url.endswith("auth/token/revoke-self")


@pytest.mark.parametrize(
    "url",
    [
        "http://vault.example.invalid",
        "https://user:password@vault.example.invalid",
        "https://vault.example.invalid?token=fixture",
        "https://vault.example.invalid/#fixture",
        "https://vault.example.invalid:not-a-port",
    ],
)
def test_refuses_insecure_or_credential_bearing_urls(monkeypatch, config, url):
    """Prueft den HTTPS-Ursprung vor jedem Netzwerkkontakt."""
    opener, _ = opener_with(monkeypatch, [])
    config["url"] = url

    with pytest.raises(OpenBaoError, match="HTTPS-Adresse"):
        read_kv2_secret(config)

    opener.open.assert_not_called()


@pytest.mark.parametrize("path", ["../smtp", "/smtp", "invoices//smtp", ".", None])
def test_refuses_ambiguous_secret_paths(monkeypatch, config, path):
    """Verhindert ungueltige API-Pfade vor dem Login."""
    opener, _ = opener_with(monkeypatch, [])
    config["path"] = path

    with pytest.raises(OpenBaoError):
        read_kv2_secret(config)

    opener.open.assert_not_called()


def test_redirect_handler_never_follows_locations():
    """Eine Weiterleitung bekommt weder AppRole-Anmeldedaten noch Sitzungstoken."""
    handler = openbao_secrets._RejectRedirects()

    result = handler.redirect_request(None, None, 302, "", {}, "https://other.invalid")

    assert result is None
