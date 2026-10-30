"""Formatiert ausdrücklich gepflegte Kontaktnamen und Briefanreden."""

SALUTATIONS = ("frau", "herr", "neutral", "organisation")


def normalize_contact_identity(contact: dict) -> dict:
    """Prüft Namensfelder und erzeugt vollständigen Namen und Briefanrede."""
    if not isinstance(contact, dict):
        raise ValueError("Kontaktidentität muss ein Objekt sein.")
    identity = {}
    for field in ("first_name", "last_name", "salutation"):
        value = contact.get(field)
        if not isinstance(value, str):
            raise ValueError(f"contact.{field} muss ausdrücklich als Text vorliegen.")
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError(f"contact.{field} darf keine Steuerzeichen enthalten.")
        identity[field] = value.strip()

    salutation = identity["salutation"]
    if salutation not in SALUTATIONS:
        raise ValueError(
            "contact.salutation muss frau, herr, neutral oder organisation sein."
        )
    full_name = " ".join(
        value for value in (identity["first_name"], identity["last_name"]) if value
    )
    if salutation in {"frau", "herr"} and not identity["last_name"]:
        raise ValueError("contact.last_name ist bei frau und herr erforderlich.")
    if salutation == "neutral" and not full_name:
        raise ValueError("Eine neutrale Anrede benötigt mindestens einen Namen.")

    if salutation == "frau":
        letter = f"Sehr geehrte Frau {identity['last_name']},"
    elif salutation == "herr":
        letter = f"Sehr geehrter Herr {identity['last_name']},"
    elif salutation == "neutral":
        letter = f"Guten Tag {full_name},"
    else:
        letter = "Sehr geehrte Damen und Herren,"
    return {**identity, "name": full_name, "mail_salutation": letter}
