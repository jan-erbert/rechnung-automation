"""Startet optionale Windmill-Funktionen in der vorhandenen Projekt-Pythonumgebung."""

import contextlib
import json
import os
from pathlib import Path
import sys
import urllib.request

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT), str(PROJECT / "src")]

from integrations.windmill import runtime  # noqa: E402

FUNCTIONS = {
    "validate": runtime.validate_project,
    "run_native": runtime.run,
    "customers": runtime.customers,
    "customer_create": runtime.new_customer,
    "customer_edit": runtime.edit_customer,
}


def load_resource(path: str) -> dict:
    """Loest Ressourcen nur im ausfuehrenden Prozess mit dessen Jobzugang auf."""
    base = os.environ.get("BASE_INTERNAL_URL", "http://server:8000").rstrip("/")
    workspace = os.environ["WM_WORKSPACE"]
    request = urllib.request.Request(
        f"{base}/api/w/{workspace}/resources/get_value_interpolated/{path}",
        headers={"Authorization": "Bearer " + os.environ["WM_TOKEN"]},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except Exception:
        raise RuntimeError("Windmill-Ressource konnte nicht geladen werden.") from None


def main() -> None:
    """Fuehrt ausschliesslich einen bekannten Einstieg aus und trennt Logs vom Ergebnis."""
    if len(sys.argv) != 2 or sys.argv[1] not in FUNCTIONS:
        raise ValueError("Unbekannter Windmill-Einstieg.")
    arguments = json.load(sys.stdin)
    if not isinstance(arguments, dict):
        raise ValueError("Eingaben muessen ein Objekt sein.")
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        owner = PROJECT.stat()
        os.setgroups([])
        os.setgid(owner.st_gid)
        os.setuid(owner.st_uid)
    os.umask(0o077)
    if sys.argv[1] == "run_native":
        arguments["resource_loader"] = load_resource
    with contextlib.redirect_stdout(sys.stderr):
        result = FUNCTIONS[sys.argv[1]](**arguments)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
