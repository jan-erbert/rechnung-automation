"""Prueft optionale Empfaengergrenzen fuer bewusst eingeschraenkte Umgebungen."""

from email.utils import getaddresses


def validate_recipient_policy(
    customers: list[dict],
    invoice_config: dict,
    allowed_domains: list[str] | None,
) -> None:
    """Prueft alle aktiven Mailziele ohne Adressen in Fehlermeldungen auszugeben."""
    if allowed_domains is None:
        return
    if (
        not isinstance(allowed_domains, list)
        or not allowed_domains
        or any(
            not isinstance(domain, str) or not domain or "@" in domain
            for domain in allowed_domains
        )
    ):
        raise ValueError("Freigegebene Maildomains sind ungueltig.")
    allowed = {domain.lower() for domain in allowed_domains}
    recipients = list(invoice_config.get("mail", {}).get("bcc") or [])
    for customer in customers:
        recipients.append(customer["email"])
        recipients.extend(customer.get("cc") or [])
    for value in recipients:
        parsed = getaddresses([value])
        if not parsed or any(
            address.count("@") != 1 or address.rsplit("@", 1)[1].lower() not in allowed
            for _, address in parsed
        ):
            raise ValueError("Mailziel liegt ausserhalb der freigegebenen Domains.")
