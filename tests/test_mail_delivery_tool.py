from types import SimpleNamespace

from tools import test_mail_delivery


def test_mail_delivery_tool_uses_normalized_password(monkeypatch, tmp_path):
    """Das SMTP-Testtool verwendet den englischen internen Passwortschluessel."""
    sent = []
    monkeypatch.setattr(test_mail_delivery, "load_settings", lambda: {})
    monkeypatch.setattr(
        test_mail_delivery,
        "create_paths",
        lambda settings: SimpleNamespace(
            base_dir=tmp_path,
            invoice_config=tmp_path / "invoice.yaml",
        ),
    )
    monkeypatch.setattr(test_mail_delivery, "configure_logging", lambda *args: None)
    monkeypatch.setattr(
        test_mail_delivery,
        "load_invoice_config",
        lambda path: {"mail": {"bcc": ["archive@example.com"]}},
    )
    monkeypatch.setattr(
        test_mail_delivery,
        "load_mail_environment",
        lambda *args: {
            "server": "smtp.example.com",
            "port": 587,
            "user": "sender@example.com",
            "password": "secret",
            "security": "starttls",
            "timeout": 30,
        },
    )
    monkeypatch.setattr(
        test_mail_delivery,
        "build_mail_test_email",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        test_mail_delivery,
        "send_email",
        lambda server, port, user, password, *args, **kwargs: sent.append(password),
    )

    assert test_mail_delivery.main() == 0
    assert sent == ["secret"]
