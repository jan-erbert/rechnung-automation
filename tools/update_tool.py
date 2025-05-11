# tools/update_tool.py

import requests
import zipfile
import io
import os
import shutil
from packaging import version
from pathlib import Path
import importlib.util

# Repo-Infos
GITHUB_OWNER = "jan-erbert"
GITHUB_REPO = "rechnung-automation"
API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

# Liste der Dateien, die ersetzt werden dürfen
UPDATABLE_FILES = [
    "main.py",
    "version.py",
    "requirements.txt",
    "vorlagen/mail_template.html",
    "vorlagen/rechnung_template.html"
]

def get_local_version():
    version_file = Path(__file__).resolve().parent.parent / "version.py"
    spec = importlib.util.spec_from_file_location("version", version_file)
    version_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(version_module)
    return version_module.__version__

def get_latest_github_release():
    response = requests.get(API_URL, timeout=10)
    response.raise_for_status()
    data = response.json()
    latest_version = data["tag_name"].lstrip("v")  # z. B. v1.1.2 → 1.1.2

    # Suche nach einer ZIP-Datei im Release-Asset
    zip_url = None
    for asset in data.get("assets", []):
        if asset["name"].endswith(".zip"):
            zip_url = asset["browser_download_url"]
            break

    if not zip_url:
        raise RuntimeError("Keine ZIP-Datei im Release gefunden.")

    return latest_version, zip_url

def download_and_install_update(zip_url):
    print("Lade neue Version herunter ...")
    try:
        response = requests.get(zip_url, timeout=10)
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            z.extractall("update_tmp")

        updated = False
        for rel_path in UPDATABLE_FILES:
            src = os.path.join("update_tmp", rel_path)
            dst = os.path.join(".", rel_path)

            if os.path.exists(src):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.move(src, dst)
                print(f"✓ Aktualisiert: {rel_path}")
                updated = True
            else:
                print(f"⚠️ Nicht enthalten: {rel_path}")

        shutil.rmtree("update_tmp", ignore_errors=True)

        if updated:
            print("✅ Update abgeschlossen. Bitte 'main.py' neu starten.")
        else:
            print("⚠️ Keine Dateien wurden aktualisiert.")

    except Exception as e:
        print(f"Fehler beim Update: {e}")

def check_for_update():
    local_version = get_local_version()
    print(f"Aktuelle Version: {local_version}")

    try:
        latest_version, zip_url = get_latest_github_release()
        print(f"Verfügbare Version auf GitHub: {latest_version}")

        if version.parse(latest_version) > version.parse(local_version):
            choice = input("Neue Version gefunden. Jetzt installieren? [j/N]: ")
            if choice.strip().lower() == "j":
                download_and_install_update(zip_url)
            else:
                print("Update abgebrochen.")
        else:
            print("Du verwendest bereits die neueste Version.")
    except Exception as e:
        print(f"Updateprüfung fehlgeschlagen: {e}")

if __name__ == "__main__":
    check_for_update()
