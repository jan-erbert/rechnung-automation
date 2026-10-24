"""Prueft CII-XML lokal gegen Profil-XSD und EN-16931-Geschaeftsregeln."""

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

RULES_DIRECTORY = (
    Path(__file__).resolve().parents[1] / "assets" / "zugferd" / "en16931-1.3.16"
)
CII_NAMESPACE = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
SVRL_NAMESPACE = "http://purl.oclc.org/dsdl/svrl"
PROFILE_ID = "urn:cen.eu:en16931:2017"


def _dependencies():
    """Laedt Zusatzbibliotheken ausschliesslich fuer ZUGFeRD-Ausgaben."""
    try:
        import drafthorse
        from lxml import etree
        from saxonche import PySaxonProcessor
    except ImportError:
        raise RuntimeError(
            "ZUGFERD_DEPENDENCY: Optionale ZUGFeRD-Komponenten fehlen."
        ) from None
    return drafthorse, etree, PySaxonProcessor


def _parse_xml(xml_bytes, etree):
    """Liest XML ohne DTD, externe Entitaeten oder Netzwerkzugriff."""
    parser = etree.XMLParser(
        resolve_entities=False,
        load_dtd=False,
        no_network=True,
        huge_tree=False,
    )
    try:
        document = etree.fromstring(xml_bytes, parser)
        if document.getroottree().docinfo.doctype:
            raise ValueError("DTD")
    except (etree.XMLSyntaxError, ValueError, TypeError):
        raise ValueError("ZUGFERD_XML: Ungueltige oder unsichere XML.") from None
    return document


def _validate_schema(document, drafthorse, etree):
    """Prueft das paketierte EN-16931-Profilschema mit lokalen Imports."""
    schema_root = Path(drafthorse.__file__).resolve().parent / "schema"

    class LocalSchemaResolver(etree.Resolver):
        """Beschraenkt Schemaimporte auf das installierte Schemapaket."""

        def resolve(self, url, public_id, context):
            """Loest ausschliesslich lokale XSD-Dateien im Schemapaket auf."""
            parsed = urlparse(url)
            if Path(url).is_absolute():
                candidate = Path(url)
            elif parsed.scheme == "file" and not parsed.netloc:
                candidate = Path(url2pathname(parsed.path))
            elif not parsed.scheme and not parsed.netloc:
                candidate = schema_root / unquote(parsed.path)
            else:
                raise ValueError("Schema import")
            candidate = candidate.resolve()
            if schema_root not in candidate.parents or candidate.suffix != ".xsd":
                raise ValueError("Schema import")
            return self.resolve_filename(str(candidate), context)

    parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)
    parser.resolvers.add(LocalSchemaResolver())
    try:
        schema_path = schema_root / "Factur-X_1.0.07_EN16931.xsd"
        schema = etree.XMLSchema(etree.parse(str(schema_path), parser))
        schema.assertValid(document)
    except etree.DocumentInvalid:
        raise ValueError(
            "ZUGFERD_XSD: XML entspricht nicht dem EN-16931-Profil."
        ) from None
    except (OSError, ValueError, etree.XMLSchemaParseError, etree.XMLSyntaxError):
        raise RuntimeError(
            "ZUGFERD_SCHEMA: Lokales Profilschema nicht nutzbar."
        ) from None


def _trusted_stylesheet(rules_directory):
    """Prueft die mitgelieferte Regeldatei vor ihrer Ausfuehrung."""
    try:
        manifest = json.loads((rules_directory / "manifest.json").read_text("utf-8"))
        stylesheet = rules_directory / "EN16931-CII-validation.xslt"
        digest = hashlib.sha256(stylesheet.read_bytes()).hexdigest()
        if digest != manifest["files"][stylesheet.name]:
            raise ValueError("Checksum")
    except (OSError, ValueError, KeyError, TypeError):
        raise RuntimeError(
            "ZUGFERD_RULES: Lokale Pruefregeln fehlen oder sind defekt."
        ) from None
    return stylesheet


def _validate_business_rules(document, etree, processor_class, rules_directory):
    """Fuehrt die offiziellen CEN-Regeln aus und meldet nur sichere Regel-IDs."""
    stylesheet = _trusted_stylesheet(rules_directory)
    try:
        with processor_class(license=False) as processor:
            processor.set_configuration_property(
                "http://saxon.sf.net/feature/allow-external-functions", "false"
            )
            processor.set_configuration_property(
                "http://saxon.sf.net/feature/allowedProtocols", ""
            )
            executable = processor.new_xslt30_processor().compile_stylesheet(
                stylesheet_text=stylesheet.read_text("utf-8")
            )
            node = processor.parse_xml(
                xml_text=etree.tostring(document, encoding="unicode")
            )
            report = executable.transform_to_string(xdm_node=node)
        result = _parse_xml(report.encode("utf-8"), etree)
    except Exception:
        raise RuntimeError("ZUGFERD_RULES: XML-Regelpruefung fehlgeschlagen.") from None
    failures = result.findall(f".//{{{SVRL_NAMESPACE}}}failed-assert")
    errors = [item for item in failures if item.get("flag", "fatal") != "warning"]
    if errors:
        rule_ids = sorted(
            {
                item.get("id", "UNKNOWN")
                for item in errors
                if re.fullmatch(r"[A-Z0-9-]{1,50}", item.get("id", "UNKNOWN"))
            }
        )
        codes = ", ".join(rule_ids[:20]) or "UNKNOWN"
        raise ValueError(f"ZUGFERD_EN16931: Geschaeftsregeln verletzt ({codes}).")


def validate_invoice_xml(xml_bytes: bytes, *, rules_directory=None) -> None:
    """Prueft CII-Profil, XSD und EN-16931-Regeln ohne externe Dienste."""
    drafthorse, etree, processor_class = _dependencies()
    document = _parse_xml(xml_bytes, etree)
    if document.tag != f"{{{CII_NAMESPACE}}}CrossIndustryInvoice":
        raise ValueError("ZUGFERD_PROFILE: Keine CII-Rechnung.")
    profile = document.find(
        ".//ram:GuidelineSpecifiedDocumentContextParameter/ram:ID",
        namespaces={
            "ram": (
                "urn:un:unece:uncefact:data:standard:"
                "ReusableAggregateBusinessInformationEntity:100"
            )
        },
    )
    if profile is None or profile.text != PROFILE_ID:
        raise ValueError("ZUGFERD_PROFILE: EN-16931-Profil erforderlich.")
    _validate_schema(document, drafthorse, etree)
    _validate_business_rules(
        document,
        etree,
        processor_class,
        Path(rules_directory) if rules_directory is not None else RULES_DIRECTORY,
    )


def check_validation_setup() -> None:
    """Prueft optionale Pakete, lokale Schema- und Regeldateien ohne Rechnungsdaten."""
    drafthorse, _, _ = _dependencies()
    schema_path = (
        Path(drafthorse.__file__).resolve().parent
        / "schema"
        / "Factur-X_1.0.07_EN16931.xsd"
    )
    if not schema_path.is_file():
        raise RuntimeError("ZUGFERD_SCHEMA: Lokales Profilschema fehlt.")
    _trusted_stylesheet(RULES_DIRECTORY)
