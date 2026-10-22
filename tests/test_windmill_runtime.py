"""Prueft Windmill-Einstiege ohne echte Daten, SMTP oder Rechnungsverarbeitung."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from integrations.windmill import runtime


def test_run_uses_supplied_resource_loader_without_windmill_client(monkeypatch):
    """Ein privater Worker kann die Ressource ueber seine eigene API laden."""
    loader = Mock(
        return_value={
            "server": "smtp.example.invalid",
            "port": 587,
            "user": "fixture-user",
            "password": "fixture-password",
        }
    )
    application = Mock(return_value=0)
    monkeypatch.setattr(runtime, "run_application", application)

    result = runtime.run("send", "f/invoices/smtp", resource_loader=loader)

    loader.assert_called_once_with("f/invoices/smtp")
    assert application.call_args.args == ("non-interactive",)
    assert application.call_args.kwargs["mail_config"]["user"] == "fixture-user"
    assert result == {"exit_code": 0}
    assert "fixture-password" not in str(result)


def test_dry_run_never_loads_smtp_resource(monkeypatch):
    """Der Dry-Run benoetigt weder Windmill-Ressourcen noch OpenBao."""
    loader = Mock(side_effect=AssertionError("must not load secrets"))
    application = Mock(return_value=0)
    monkeypatch.setattr(runtime, "run_application", application)

    runtime.run(resource_loader=loader)

    loader.assert_not_called()
    assert application.call_args.args == ("dry-run",)
    assert application.call_args.kwargs["mail_config"]["port"] == 1


def test_customer_contact_fields_are_delegated_without_saving(monkeypatch, tmp_path):
    """Das Formular reicht Stammdaten nur an die gemeinsame Vorschaufunktion durch."""
    paths = SimpleNamespace(customers_dir=tmp_path, data_dir=tmp_path)
    monkeypatch.setattr(runtime, "project_paths", lambda: paths)
    monkeypatch.setattr(
        runtime, "get_customer", Mock(return_value={"revision": "fixture-revision"})
    )
    update = Mock(return_value={"applied": False})
    monkeypatch.setattr(runtime, "update_customer", update)

    result = runtime.edit_customer(
        "fixture",
        company="Fixture Company",
        contact_name="Fixture Contact",
        street="Fixture Street",
        postal_code="00000",
        city="Fixture City",
        email="fixture@example.invalid",
        cc=[],
    )

    assert result == {"applied": False}
    assert update.call_args.args[3] == {
        "contact": {
            "company": "Fixture Company",
            "name": "Fixture Contact",
            "street": "Fixture Street",
            "postal_code": "00000",
            "city": "Fixture City",
            "email": "fixture@example.invalid",
            "cc": [],
        }
    }
    assert update.call_args.kwargs["expected_revision"] == "fixture-revision"
    assert update.call_args.kwargs["apply"] is False
    assert list(tmp_path.iterdir()) == []


def test_customer_write_still_requires_preview_revision(monkeypatch, tmp_path):
    """Ein Schreibaufruf ohne vorherige Revision erreicht keine Speicherfunktion."""
    paths = SimpleNamespace(customers_dir=tmp_path, data_dir=tmp_path)
    monkeypatch.setattr(runtime, "project_paths", lambda: paths)
    monkeypatch.setattr(
        runtime, "get_customer", Mock(return_value={"revision": "fixture-revision"})
    )
    update = Mock()
    monkeypatch.setattr(runtime, "update_customer", update)

    with pytest.raises(ValueError, match="Zuerst Vorschau"):
        runtime.edit_customer("fixture", city="Fixture City", apply=True)

    update.assert_not_called()


@pytest.mark.parametrize("archive_directory", [None, "prepared-archive/fixture"])
@pytest.mark.parametrize("apply", [False, True])
def test_new_customer_preserves_optional_archive(
    monkeypatch, tmp_path, archive_directory, apply
):
    """Anlage und Vorschau uebernehmen Archive ohne das Archivziel anzulegen."""
    paths = SimpleNamespace(
        customers_dir=tmp_path / "customers", data_dir=tmp_path / "state"
    )
    monkeypatch.setattr(runtime, "project_paths", lambda: paths)
    if archive_directory is not None:
        archive_directory = str(tmp_path / archive_directory)
    options = {"archive_directory": archive_directory} if archive_directory else {}

    result = runtime.new_customer(
        customer_id="fixture",
        company="Fixture Company",
        contact_name="Fixture Contact",
        email="fixture@example.invalid",
        street="Fixture Street",
        postal_code="00000",
        city="Fixture City",
        description="Hosting",
        unit_price="50.00",
        apply=apply,
        **options,
    )

    assert result["customer"]["archive"] == {"directory": archive_directory}
    assert result["saved"] is apply
    assert not (tmp_path / "prepared-archive").exists()
    if apply:
        saved = runtime.get_customer(paths.customers_dir, "fixture")
        assert saved["customer"]["archive"] == {"directory": archive_directory}
        assert sorted(path.name for path in paths.data_dir.iterdir()) == [
            ".invoice-run.lock",
        ]
    else:
        assert list(tmp_path.iterdir()) == []
