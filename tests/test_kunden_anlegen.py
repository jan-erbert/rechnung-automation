from tools.kunden_anlegen import frage_mail_cc, frage_validiert
from validierung import validiere_positive_ganzzahl


def test_frage_validiert_repeats_after_invalid_input(monkeypatch, capsys):
    """Die Kundenanlage fragt nach einer ungueltigen Eingabe erneut."""
    eingaben = iter(["monatlich", "3"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(eingaben))

    wert = frage_validiert(
        "Abrechnungszyklus: ",
        lambda eingabe: validiere_positive_ganzzahl(
            eingabe,
            "Abrechnungszyklus",
        ),
    )

    assert wert == "3"
    assert "Ungueltige Eingabe" in capsys.readouterr().out


def test_frage_mail_cc_collects_multiple_addresses(monkeypatch):
    """Die Kundenanlage sammelt mehrere optionale CC-Adressen."""
    eingaben = iter(["cc@example.com", "team@example.com", ""])
    monkeypatch.setattr("builtins.input", lambda prompt: next(eingaben))

    assert frage_mail_cc() == ["cc@example.com", "team@example.com"]
