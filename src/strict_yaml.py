from pathlib import Path

import yaml


class UniqueKeyLoader(yaml.SafeLoader):
    """Laedt YAML sicher und lehnt doppelte Schluessel ab."""


def _construct_unique_mapping(loader, node, deep=False):
    """Erzeugt eine Map und meldet doppelte YAML-Schluessel."""
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"duplicate key: {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def load_yaml(path: Path):
    """Laedt eine YAML-Datei mit strikter Duplicate-Key-Pruefung."""
    try:
        with path.open("r", encoding="utf-8") as yaml_file:
            return yaml.load(yaml_file, Loader=UniqueKeyLoader)
    except yaml.YAMLError as err:
        raise ValueError(f"Ungueltiges YAML in '{path.name}': {err}") from err


def reject_unknown_keys(data: dict, allowed: set[str], section: str) -> None:
    """Lehnt unbekannte Konfigurationsschluessel eines Bereichs ab."""
    unknown = sorted(set(data) - allowed)
    if unknown:
        joined = ", ".join(f"{section}.{key}" for key in unknown)
        raise ValueError(f"Unbekannte Felder: {joined}")
