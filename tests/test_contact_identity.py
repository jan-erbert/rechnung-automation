"""Prüft explizite Briefanreden ohne Namens- oder Geschlechtsraten."""

import pytest

from contact_identity import normalize_contact_identity


@pytest.mark.parametrize(
    "first,last,salutation,expected",
    [
        ("Erika", "Beispiel", "frau", "Sehr geehrte Frau Beispiel,"),
        ("Max", "Mustermann", "herr", "Sehr geehrter Herr Mustermann,"),
        ("Alex", "von der Heide", "neutral", "Guten Tag Alex von der Heide,"),
        ("", "Müller-Schmidt", "frau", "Sehr geehrte Frau Müller-Schmidt,"),
        ("Alex", "", "neutral", "Guten Tag Alex,"),
        ("", "", "organisation", "Sehr geehrte Damen und Herren,"),
    ],
)
def test_explicit_letter_salutations(first, last, salutation, expected):
    """Die gewählte Anrede bestimmt ausschließlich die Briefansprache."""
    result = normalize_contact_identity(
        {"first_name": first, "last_name": last, "salutation": salutation}
    )
    assert result["mail_salutation"] == expected
    assert result["name"] == " ".join(value for value in (first, last) if value)


@pytest.mark.parametrize("salutation", ["frau", "herr"])
def test_formal_salutations_require_last_name(salutation):
    """Eine förmliche Anrede darf nicht auf den Vornamen zurückfallen."""
    with pytest.raises(ValueError, match="last_name"):
        normalize_contact_identity(
            {"first_name": "Alex", "last_name": "", "salutation": salutation}
        )


@pytest.mark.parametrize(
    "contact",
    [
        {"name": "Frau Beispiel"},
        {"first_name": "Alex", "last_name": "Beispiel"},
        {"first_name": "Alex", "last_name": "Beispiel", "salutation": "auto"},
        {"first_name": "", "last_name": "", "salutation": "neutral"},
        {"first_name": "Alex\nTest", "last_name": "Beispiel", "salutation": "herr"},
        {"first_name": 42, "last_name": "Beispiel", "salutation": "neutral"},
    ],
)
def test_missing_or_invalid_identity_is_rejected(contact):
    """Unvollständige Altfelder und implizite Geschlechtsableitung sind unzulässig."""
    with pytest.raises(ValueError):
        normalize_contact_identity(contact)


def test_names_do_not_determine_salutation():
    """Derselbe Vorname kann mit jeder ausdrücklich gewählten Anrede verwendet werden."""
    contact = {"first_name": "Alex", "last_name": "Beispiel", "salutation": "frau"}
    assert "Frau Beispiel" in normalize_contact_identity(contact)["mail_salutation"]
    contact["salutation"] = "herr"
    assert "Herr Beispiel" in normalize_contact_identity(contact)["mail_salutation"]


def test_display_name_is_trimmed_without_honorific():
    """Im Adressblock bleibt der vollständige Personenname ohne Anredetitel."""
    result = normalize_contact_identity(
        {"first_name": " Erika ", "last_name": " Beispiel ", "salutation": "frau"}
    )
    assert result["name"] == "Erika Beispiel"
