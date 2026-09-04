import os
import re
import tempfile
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml

CUSTOMER_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PERIOD_PATTERN = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])$")
HUNDREDTH = Decimal("0.01")


class _UniqueKeyLoader(yaml.SafeLoader):
    """Laedt YAML sicher und lehnt doppelte Schluessel ab."""


class _HoursDumper(yaml.SafeDumper):
    """Schreibt Decimal-Stundenwerte als gut lesbare YAML-Zahlen."""


def _construct_unique_mapping(loader, node, deep=False):
    """Erzeugt eine Map und meldet doppelte YAML-Schluessel."""
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"duplicate key: {key}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


def _construct_decimal(loader, node) -> Decimal:
    """Laedt eine YAML-Gleitkommazahl ohne binaeren Genauigkeitsverlust."""
    value = loader.construct_scalar(node)
    normalized = value.replace("_", "").lower()
    if normalized in (".inf", "+.inf"):
        normalized = "Infinity"
    elif normalized == "-.inf":
        normalized = "-Infinity"
    elif normalized == ".nan":
        normalized = "NaN"
    return Decimal(normalized)


def _represent_decimal(dumper, value: Decimal):
    """Schreibt Decimal als YAML-Zahl mit zwei Nachkommastellen."""
    return dumper.represent_scalar("tag:yaml.org,2002:float", f"{value:.2f}")


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)
_UniqueKeyLoader.add_constructor(
    "tag:yaml.org,2002:float",
    _construct_decimal,
)
_HoursDumper.add_representer(Decimal, _represent_decimal)


class HoursFileError(ValueError):
    """Kennzeichnet eine ungueltige oder widerspruechliche Stundendatei."""


def hours_file_path(hours_dir: Path, period: str) -> Path:
    """Liefert den YAML-Pfad fuer einen monatlichen Stundenzeitraum."""
    _validate_period(period)
    return hours_dir / f"{period}.yaml"


def load_hours_month(file_path: Path, expected_period: str) -> dict[str, Decimal]:
    """Laedt und validiert die Stundenwerte eines Monats."""
    _validate_period(expected_period)
    try:
        with file_path.open("r", encoding="utf-8") as hours_file:
            data = yaml.load(hours_file, Loader=_UniqueKeyLoader)
    except OSError as err:
        raise HoursFileError(
            f"Stundendatei '{file_path.name}' konnte nicht gelesen werden."
        ) from err
    except yaml.YAMLError as err:
        raise HoursFileError(
            f"Stundendatei '{file_path.name}' enthaelt ungueltiges YAML."
        ) from err

    if not isinstance(data, dict):
        raise HoursFileError(
            f"Stundendatei '{file_path.name}' muss eine YAML-Map enthalten."
        )
    unknown_fields = set(data) - {"period", "customers"}
    if unknown_fields:
        raise HoursFileError(
            f"Stundendatei '{file_path.name}': unbekannte Felder: "
            + ", ".join(sorted(unknown_fields))
        )
    if data.get("period") != expected_period:
        raise HoursFileError(
            f"Stundendatei '{file_path.name}': period muss "
            f"'{expected_period}' sein."
        )
    customers = data.get("customers")
    if not isinstance(customers, dict):
        raise HoursFileError(
            f"Stundendatei '{file_path.name}': customers muss eine Map sein."
        )

    result = {}
    for customer_id, entry in customers.items():
        if not isinstance(customer_id, str) or not CUSTOMER_ID_PATTERN.fullmatch(
            customer_id
        ):
            raise HoursFileError(
                f"Stundendatei '{file_path.name}': ungueltige Kunden-ID."
            )
        if not isinstance(entry, dict):
            raise HoursFileError(
                f"Stundendatei '{file_path.name}': Eintrag fuer '{customer_id}' "
                "muss eine Map sein."
            )
        unknown_fields = set(entry) - {"hours"}
        if unknown_fields:
            raise HoursFileError(
                f"Stundendatei '{file_path.name}', Kunde '{customer_id}': "
                "unbekannte Felder: " + ", ".join(sorted(unknown_fields))
            )
        result[customer_id] = validate_hours_value(
            entry.get("hours"),
            f"Stundendatei '{file_path.name}', Kunde '{customer_id}'",
        )
    return result


def validate_hours_value(value, field: str = "hours") -> Decimal:
    """Prueft einen numerischen oder als Text notierten Stundenwert."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise HoursFileError(f"{field}: hours muss eine Zahl sein.")
    text = str(value).strip().replace(",", ".")
    try:
        hours = Decimal(text)
    except InvalidOperation as err:
        raise HoursFileError(
            f"{field}: hours muss eine nichtnegative Dezimalzahl sein."
        ) from err
    if not hours.is_finite() or hours < 0:
        raise HoursFileError(
            f"{field}: hours muss eine nichtnegative Dezimalzahl sein."
        )
    if hours.quantize(HUNDREDTH) != hours:
        raise HoursFileError(
            f"{field}: hours darf hoechstens zwei Nachkommastellen haben."
        )
    return hours


def save_hours_value(
    hours_dir: Path,
    period: str,
    customer_id: str,
    hours: Decimal,
) -> Path:
    """Speichert einen manuell erfassten Stundenwert atomar im Monats-YAML."""
    file_path = hours_file_path(hours_dir, period)
    existing_values = load_hours_month(file_path, period) if file_path.exists() else {}
    existing_values[customer_id] = hours
    write_hours_month(file_path, period, existing_values)
    return file_path


def write_hours_month(
    file_path: Path,
    period: str,
    hours_values: dict[str, Decimal],
    replace_existing: bool = True,
) -> None:
    """Schreibt eine validierte Monatsdatei atomar als YAML."""
    _validate_period(period)
    if file_path.name != f"{period}.yaml":
        raise HoursFileError(
            f"Dateiname muss fuer period '{period}' '{period}.yaml' sein."
        )
    if file_path.exists() and not replace_existing:
        raise FileExistsError(f"Zieldatei existiert bereits: {file_path}")
    customers = {}
    for customer_id, hours in sorted(hours_values.items()):
        if not CUSTOMER_ID_PATTERN.fullmatch(customer_id):
            raise HoursFileError(f"Ungueltige Kunden-ID: '{customer_id}'.")
        validated_value = validate_hours_value(str(hours), customer_id)
        customers[customer_id] = {"hours": validated_value}

    file_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=file_path.parent,
            prefix=f".{file_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            yaml.dump(
                {"period": period, "customers": customers},
                temporary_file,
                Dumper=_HoursDumper,
                allow_unicode=True,
                sort_keys=False,
            )
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, file_path)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def period_from_date(value: date | datetime) -> str:
    """Formatiert ein Datum als monatlichen Stundenzeitraum."""
    return value.strftime("%Y-%m")


def _validate_period(period: str) -> None:
    """Prueft einen Monatszeitraum im Format JJJJ-MM."""
    if not isinstance(period, str) or not PERIOD_PATTERN.fullmatch(period):
        raise HoursFileError("period muss dem Format JJJJ-MM entsprechen.")
