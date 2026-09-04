import base64
import logging
from dataclasses import dataclass
from pathlib import Path

from strict_yaml import reject_unknown_keys

logger = logging.getLogger(__name__)

DEFAULT_BRANDING = {
    "pdf_logo": "logo.png",
    "mail_logo": None,
    "pdf_logo_height": 40,
    "mail_logo_height": 60,
    "header_title": None,
    "header_subtitle": None,
}
SUPPORTED_LOGO_FORMATS = {
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


def validate_branding_config(branding_config: dict | None) -> dict:
    """Prueft Logoangaben und ergaenzt die Branding-Standardwerte."""
    if branding_config is None:
        branding_config = {}
    if not isinstance(branding_config, dict):
        raise ValueError("Der YAML-Bereich 'branding' muss eine Map sein.")

    reject_unknown_keys(branding_config, set(DEFAULT_BRANDING), "branding")
    validated = {}
    for name in ("pdf_logo", "mail_logo"):
        default = DEFAULT_BRANDING[name]
        value = branding_config.get(name, default)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"branding.{name} muss ein Dateipfad oder null sein.")
        if value is not None:
            _detect_logo_subtype(Path(value))
        validated[name] = value

    for name in ("header_title", "header_subtitle"):
        value = branding_config.get(name)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"branding.{name} muss ein Text oder null sein.")
        validated[name] = value

    for name in ("pdf_logo_height", "mail_logo_height"):
        value = branding_config.get(name, DEFAULT_BRANDING[name])
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 10 <= value <= 200
        ):
            raise ValueError(f"branding.{name} muss eine Ganzzahl von 10 bis 200 sein.")
        validated[name] = value
    return validated


def resolve_logo_path(image_dir: Path, path_value: str) -> Path:
    """Loest einen absoluten oder im Bildordner liegenden Logo-Pfad auf."""
    logo_path = Path(path_value).expanduser()
    if logo_path.is_absolute():
        return logo_path

    image_dir = image_dir.resolve()
    logo_path = (image_dir / logo_path).resolve()
    try:
        logo_path.relative_to(image_dir)
    except ValueError as err:
        raise ValueError(
            "Relative Logo-Pfade muessen innerhalb von paths.image_dir liegen."
        ) from err
    return logo_path


def load_logo_asset(
    image_dir: Path,
    path_value: str | None,
    label: str,
) -> LogoAsset | None:
    """Laedt ein optionales PNG- oder JPEG-Logo."""
    if path_value is None:
        return None

    logo_path = resolve_logo_path(image_dir, path_value)
    subtype = _detect_logo_subtype(logo_path)
    try:
        data = logo_path.read_bytes()
    except FileNotFoundError:
        logger.warning("%s nicht gefunden. Es wird kein Logo verwendet.", label)
        return None
    except OSError as err:
        logger.warning("%s ist nicht lesbar und wird ignoriert: %s", label, err)
        return None

    return LogoAsset(data=data, subtype=subtype)


def _detect_logo_subtype(logo_path: Path) -> str:
    """Ermittelt den MIME-Subtype eines unterstuetzten Logoformats."""
    subtype = SUPPORTED_LOGO_FORMATS.get(logo_path.suffix.lower())
    if subtype is None:
        raise ValueError(
            "Logo-Dateien muessen das Format .png, .jpg oder .jpeg verwenden."
        )
    return subtype
