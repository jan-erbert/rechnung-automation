import base64
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_BRANDING = {
    "pdf_logo": "logo.png",
    "mail_logo": None,
    "pdf_logo_height": 40,
    "mail_logo_height": 60,
    "header_title": None,
    "header_subtitle": None,
}
UNTERSTUETZTE_LOGO_FORMATE = {
    ".png": "png",
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
}


@dataclass(frozen=True)
class LogoAsset:
    """Enthaelt ein geladenes Logo fuer PDF oder Mail."""

    data: bytes
    subtype: str

    @property
    def data_uri(self) -> str:
        """Erzeugt eine Data-URI fuer die PDF-Vorlage."""
        encoded = base64.b64encode(self.data).decode("ascii")
        return f"data:image/{self.subtype};base64,{encoded}"


def validiere_branding_config(branding_config: dict | None) -> dict:
    """Prueft Logoangaben und ergaenzt die Branding-Standardwerte."""
    if branding_config is None:
        branding_config = {}
    if not isinstance(branding_config, dict):
        raise ValueError("Der YAML-Bereich 'branding' muss eine Map sein.")

    validiert = {}
    for name in ("pdf_logo", "mail_logo"):
        standardwert = DEFAULT_BRANDING[name]
        wert = branding_config.get(name, standardwert)
        if wert is not None and (not isinstance(wert, str) or not wert.strip()):
            raise ValueError(f"branding.{name} muss ein Dateipfad oder null sein.")
        if wert is not None:
            _ermittle_logo_subtype(Path(wert))
        validiert[name] = wert

    for name in ("header_title", "header_subtitle"):
        wert = branding_config.get(name)
        if wert is not None and (not isinstance(wert, str) or not wert.strip()):
            raise ValueError(f"branding.{name} muss ein Text oder null sein.")
        validiert[name] = wert

    for name in ("pdf_logo_height", "mail_logo_height"):
        wert = branding_config.get(name, DEFAULT_BRANDING[name])
        if isinstance(wert, bool) or not isinstance(wert, int) or not 10 <= wert <= 200:
            raise ValueError(f"branding.{name} muss eine Ganzzahl von 10 bis 200 sein.")
        validiert[name] = wert
    return validiert


def loese_logo_pfad_auf(image_dir: Path, pfad_wert: str) -> Path:
    """Loest einen absoluten oder im Bildordner liegenden Logo-Pfad auf."""
    logo_pfad = Path(pfad_wert).expanduser()
    if logo_pfad.is_absolute():
        return logo_pfad

    image_dir = image_dir.resolve()
    logo_pfad = (image_dir / logo_pfad).resolve()
    try:
        logo_pfad.relative_to(image_dir)
    except ValueError as err:
        raise ValueError(
            "Relative Logo-Pfade muessen innerhalb von paths.image_dir liegen."
        ) from err
    return logo_pfad


def lade_logo_asset(
    image_dir: Path,
    pfad_wert: str | None,
    bezeichnung: str,
) -> LogoAsset | None:
    """Laedt ein optionales PNG- oder JPEG-Logo."""
    if pfad_wert is None:
        return None

    logo_pfad = loese_logo_pfad_auf(image_dir, pfad_wert)
    subtype = _ermittle_logo_subtype(logo_pfad)
    try:
        data = logo_pfad.read_bytes()
    except FileNotFoundError:
        logger.warning("%s nicht gefunden. Es wird kein Logo verwendet.", bezeichnung)
        return None
    except OSError as err:
        logger.warning("%s ist nicht lesbar und wird ignoriert: %s", bezeichnung, err)
        return None

    return LogoAsset(data=data, subtype=subtype)


def _ermittle_logo_subtype(logo_pfad: Path) -> str:
    """Ermittelt den MIME-Subtype eines unterstuetzten Logoformats."""
    subtype = UNTERSTUETZTE_LOGO_FORMATE.get(logo_pfad.suffix.lower())
    if subtype is None:
        raise ValueError(
            "Logo-Dateien muessen das Format .png, .jpg oder .jpeg verwenden."
        )
    return subtype
