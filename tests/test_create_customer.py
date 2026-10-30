import pytest

from tools.create_customer import ask_contact_identity, ask_email_cc, ask_validated
from validation import validate_positive_integer


def test_frage_validiert_repeats_after_invalid_input(monkeypatch, capsys):
    """Die Kundenanlage fragt nach einer ungueltigen Eingabe erneut."""
    eingaben = iter(["monatlich", "3"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(eingaben))

    value = ask_validated(
        "Abrechnungszyklus: ",
        lambda input_value: validate_positive_integer(
            input_value,
            "Abrechnungszyklus",
        ),
    )

    assert value == "3"
    assert "Ungueltige Eingabe" in capsys.readouterr().out


def test_frage_mail_cc_collects_multiple_addresses(monkeypatch):
    """Die Kundenanlage sammelt mehrere optionale CC-Adressen."""
    eingaben = iter(["cc@example.com", "team@example.com", ""])
    monkeypatch.setattr("builtins.input", lambda prompt: next(eingaben))

    assert ask_email_cc() == ["cc@example.com", "team@example.com"]


@pytest.mark.parametrize(
    ("salutation", "first_name", "last_name", "expected"),
    [
        ("frau", "Erika", "Beispiel", "Sehr geehrte Frau Beispiel,"),
        ("herr", "Max", "Mustermann", "Sehr geehrter Herr Mustermann,"),
        ("neutral", "Alex", "Beispiel", "Guten Tag Alex Beispiel,"),
        ("organisation", "", "", "Sehr geehrte Damen und Herren,"),
    ],
)
def test_contact_identity_is_collected_explicitly(
    monkeypatch, salutation, first_name, last_name, expected
):
    """Die CLI uebernimmt die bewusste Auswahl statt aus Namen zu raten."""
    values = iter([salutation, first_name, last_name])
    monkeypatch.setattr("builtins.input", lambda prompt: next(values))

    contact = ask_contact_identity()

    assert contact["first_name"] == first_name
    assert contact["last_name"] == last_name
    assert contact["salutation"] == salutation
    assert contact["mail_salutation"] == expected


def test_formal_contact_repeats_if_last_name_is_missing(monkeypatch, capsys):
    """Eine formelle Anrede wird nicht mit einem leeren Nachnamen gespeichert."""
    values = iter(["frau", "Erika", "", "frau", "Erika", "Beispiel"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(values))

    contact = ask_contact_identity()

    assert contact["last_name"] == "Beispiel"
    assert "Ungueltige Kontaktangaben" in capsys.readouterr().out
