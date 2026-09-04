from tools.create_customer import ask_email_cc, ask_validated
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
