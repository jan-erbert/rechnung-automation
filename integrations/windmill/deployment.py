"""Erstellt portable Windmill-Skripte und einen versionierbaren Flow."""

import inspect
import json

import yaml
from pathlib import Path

from integrations.windmill import runtime

FUNCTIONS = {
    "validate": ("validate_project", "Konfiguration pruefen"),
    "run_native": ("run", "Rechnungslauf"),
    "customers": ("customers", "Kunden anzeigen"),
    "customer_create": ("new_customer", "Kunde anlegen"),
    "customer_edit": ("edit_customer", "Kunde bearbeiten"),
}


def _schema(function) -> dict:
    """Baut Formularfelder aus den gemeinsamen Verwaltungsfunktionen."""
    properties = {}
    required = []
    for name, parameter in inspect.signature(function).parameters.items():
        if name in {"allowed_domains", "resource_loader"}:
            continue
        field = {"type": "string", "title": name.replace("_", " ")}
        if name in {"apply", "active"}:
            field["type"] = "boolean"
        elif name == "cycle_months":
            field.update(type="integer", minimum=1)
        elif name == "cc":
            field.update(type="array", items={"type": "string"})
        if name == "mode":
            field["enum"] = ["dry-run", "send"]
        if parameter.default is inspect.Parameter.empty:
            required.append(name)
        else:
            field["default"] = parameter.default
            if parameter.default is None:
                field["nullable"] = True
        if name == "active" and parameter.default is None:
            field = {
                "type": "string",
                "title": "Kundenstatus (unveraendert / aktiv / inaktiv)",
                "enum": ["unchanged", "active", "inactive"],
                "default": "unchanged",
            }
        if name == "effective_from":
            field["description"] = (
                "Optional JJJJ-MM; leer = naechste zulaessige Periode."
            )
        if name == "expected_revision":
            field["description"] = (
                "revision aus der Vorschau; fuer Speichern erforderlich."
            )
        if name == "apply":
            field["title"] = "Aenderung speichern (sonst nur Vorschau)"
        properties[name] = field
    return {"type": "object", "properties": properties, "required": required}


def script_definitions(
    project_root: str,
    allowed_domains: list[str] | None = None,
    python_executable: str = "python3",
) -> list[dict]:
    """Erzeugt schlanke Einstiegsskripte ohne Kopie der fachlichen Verarbeitung."""
    if not Path(project_root).is_absolute():
        raise ValueError("Der Worker-Projektpfad muss absolut sein.")
    prefix = "import json\nimport subprocess\nfrom pathlib import Path\n"
    prefix += f"PROJECT = Path({project_root!r})\n"
    prefix += f"PYTHON = {python_executable!r}\n"
    prefix += "\ndef invoke(action, arguments):\n"
    prefix += '    """Verwendet die eigene Projekt-Pythonumgebung."""\n'
    prefix += (
        "    result = subprocess.run([PYTHON, "
        "str(PROJECT / 'integrations/windmill/bridge.py'), action], "
        "input=json.dumps(arguments), capture_output=True, text=True, timeout=330)\n"
    )
    prefix += (
        "    if result.stderr:\n        import logging\n"
        "        logging.getLogger(__name__).warning('%s', result.stderr.rstrip())\n"
    )
    prefix += (
        "    if result.returncode:\n"
        "        raise RuntimeError('Projektaufruf fehlgeschlagen; siehe Laufprotokoll.')\n"
    )
    prefix += "    return json.loads(result.stdout)\n"
    result = []
    for name, (function_name, summary) in FUNCTIONS.items():
        function = getattr(runtime, function_name)
        parameters = [
            p
            for p in inspect.signature(function).parameters.values()
            if p.name not in {"allowed_domains", "resource_loader"}
        ]
        parameters = [
            p.replace(annotation=str, default="unchanged")
            if p.name == "active" and p.default is None
            else p
            for p in parameters
        ]
        signature = inspect.signature(function).replace(parameters=parameters)
        arguments = [
            "'active': {'unchanged': None, 'active': True, 'inactive': False}[active]"
            if p.name == "active" and p.default == "unchanged"
            else f"{p.name!r}: {p.name}"
            for p in parameters
        ]
        if "allowed_domains" in inspect.signature(function).parameters:
            arguments.append(f"'allowed_domains': {allowed_domains!r}")
        content = prefix + f"\ndef main{signature}:\n"
        content += '    """Verwendet die gemeinsame versionierte Anwendung."""\n'
        content += f"    return invoke({name!r}, {{{', '.join(arguments)}}})\n"
        result.append(
            {
                "path": "f/rechnung/" + name,
                "summary": summary,
                "description": (
                    "Optionaler Einstieg aus dem versionierten Anwendungsrepository."
                ),
                "content": content,
                "language": "python3",
                "lock": "",
                "tag": "python3",
                "schema": _schema(function),
                "timeout": 360,
            }
        )
    return result


def invoice_flow() -> dict:
    """Verbindet Pruefung, Rechnungslauf und Ergebnis ohne automatische Wiederholung."""
    path = Path(__file__).with_name("invoice.flow.yaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    print(json.dumps(invoice_flow(), ensure_ascii=False, indent=2))
