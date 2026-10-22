"""Prueft Mailzielgrenzen ohne Zugriff auf SMTP oder private Dateien."""

import pytest

from recipient_policy import validate_recipient_policy


def test_public_default_has_no_private_domain_dependency():
    """Die allgemeine Anwendung hat keine fest eingebaute Betreiber-Maildomain."""
    validate_recipient_policy([{"email": "fixture@example.invalid"}], {}, None)


@pytest.mark.parametrize("location", ["to", "cc", "bcc"])
def test_every_recipient_location_is_restricted(location):
    """To, CC und Betreiber-BCC unterliegen derselben optionalen Begrenzung."""
    customer = {"email": "fixture@allowed.invalid", "cc": []}
    config = {"mail": {"bcc": []}}
    if location == "to":
        customer["email"] = "fixture@outside.invalid"
    elif location == "cc":
        customer["cc"] = ["fixture@outside.invalid"]
    else:
        config["mail"]["bcc"] = ["fixture@outside.invalid"]
    with pytest.raises(ValueError, match="freigegebenen") as error:
        validate_recipient_policy([customer], config, ["allowed.invalid"])
    assert "fixture@" not in str(error.value)
