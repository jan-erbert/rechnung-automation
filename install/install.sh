#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
CONFIG_WRITER="$SCRIPT_DIR/write_config.py"
ENV_WRITER="$SCRIPT_DIR/write_env.py"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

function pflicht_eingabe() {
    local prompt="$1"
    local eingabe=""
    while [ -z "$eingabe" ]; do
        read -r -p "$prompt: " eingabe
        if [ -z "$eingabe" ]; then
            echo "⚠️  Dieses Feld darf nicht leer sein." >&2
        fi
    done
    printf '%s' "$eingabe"
}

function port_eingabe() {
    local prompt="$1"
    local eingabe=""
    while true; do
        eingabe=$(pflicht_eingabe "$prompt")
        if [[ "$eingabe" =~ ^[0-9]+$ ]] &&
            [ "$eingabe" -gt 0 ] &&
            [ "$eingabe" -le 65535 ]; then
            printf '%s' "$eingabe"
            return
        fi
        echo "⚠️  Bitte einen Port zwischen 1 und 65535 eingeben." >&2
    done
}

function pflicht_geheim_eingabe() {
    local prompt="$1"
    local eingabe=""
    while [ -z "$eingabe" ]; do
        read -r -s -p "$prompt: " eingabe
        echo "" >&2
        if [ -z "$eingabe" ]; then
            echo "⚠️  Dieses Feld darf nicht leer sein." >&2
        fi
    done
    printf '%s' "$eingabe"
}

function prozent_eingabe() {
    local prompt="$1"
    local eingabe=""
    while true; do
        eingabe=$(pflicht_eingabe "$prompt")
        if [[ "$eingabe" =~ ^[0-9]+$ ]] && [ "$eingabe" -le 100 ]; then
            printf '%s' "$eingabe"
            return
        fi
        echo "⚠️  Bitte einen ganzzahligen Prozentsatz zwischen 0 und 100 eingeben." >&2
    done
}

function ja_nein_eingabe() {
    local prompt="$1"
    local eingabe=""
    while true; do
        read -r -p "$prompt: " eingabe
        case "${eingabe,,}" in
            y|yes|j|ja)
                printf 'y'
                return
                ;;
            n|no|nein)
                printf 'n'
                return
                ;;
            *)
                echo "⚠️  Bitte y oder n eingeben." >&2
                ;;
        esac
    done
}

cd "$PROJECT_ROOT" || exit 1

echo "🔧 Starte Einrichtung der virtuellen Umgebung..."

if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ python3 wurde nicht gefunden. Bitte installiere Python 3."
    exit 1
fi

# 1. Virtuelle Umgebung erstellen
if [ ! -x "$VENV_PYTHON" ]; then
    if [ -e ".venv" ]; then
        echo "❌ .venv ist vorhanden, aber unvollständig oder nicht verwendbar."
        echo "   Bitte den Ordner .venv entfernen und den Installer erneut starten."
        exit 1
    fi
    python3 -m venv .venv
    echo "✅ Virtuelle Umgebung wurde erstellt."
else
    echo "🔁 .venv bereits vorhanden."
fi

# 2. Hinweis zur Aktivierung
echo ""
echo "💡 Bitte aktiviere die Umgebung mit:"
echo "   source .venv/bin/activate"
echo ""

# 3. Abhängigkeiten installieren
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "❌ Requirements-Datei nicht gefunden: $REQUIREMENTS_FILE"
    exit 1
fi
echo "📦 Installiere Pakete aus $REQUIREMENTS_FILE..."
"$VENV_PYTHON" -m pip install -r "$REQUIREMENTS_FILE"

# 4. Env-Datei erstellen
ENV_PATH=".env"
if [ ! -f "$ENV_PATH" ]; then
    echo ""
    echo "📧 Mail-Umgebung wird erstellt ($ENV_PATH)..."
    echo ""

    mail_server=$(pflicht_eingabe "SMTP-Server")
    mail_port=$(port_eingabe "SMTP-Port (z. B. 587)")
    mail_user=$(pflicht_eingabe "SMTP-Benutzer")
    mail_pass=$(pflicht_geheim_eingabe "SMTP-Passwort")

    if [ ! -f "$ENV_WRITER" ]; then
        echo "❌ Env-Helfer nicht gefunden: $ENV_WRITER"
        exit 1
    fi

    export MAIL_SERVER="$mail_server"
    export MAIL_PORT="$mail_port"
    export MAIL_USER="$mail_user"
    export MAIL_PASS="$mail_pass"
    "$VENV_PYTHON" "$ENV_WRITER" "$ENV_PATH"
    unset MAIL_SERVER MAIL_PORT MAIL_USER MAIL_PASS

    echo "✅ .env wurde gespeichert unter: $ENV_PATH"
else
    echo "🗂️  .env ist bereits vorhanden – keine Änderungen vorgenommen."
fi

# 5. Konfigurationsdatei erstellen
KONFIG_PATH="data/konfiguration.json"
if [ ! -f "$KONFIG_PATH" ]; then
    echo ""
    echo "🛠️  Konfigurationsdatei wird erstellt ($KONFIG_PATH)..."
    echo ""

    name=$(pflicht_eingabe "👤 Dein Name (z. B. Jan Erbert)")
    firma=$(pflicht_eingabe "🏢 Firmenname (z. B. Web Development)")
    strasse=$(pflicht_eingabe "📍 Straße und Hausnummer")
    plz=$(pflicht_eingabe "📮 PLZ")
    ort=$(pflicht_eingabe "🌆 Ort")
    telefon=$(pflicht_eingabe "📞 Telefonnummer")
    email=$(pflicht_eingabe "📧 E-Mail-Adresse")
    read -r -p "🔗 Webseite (optional): " website

    bankname=$(pflicht_eingabe "🏦 Bankname")
    kontoinhaber=$(pflicht_eingabe "👤 Kontoinhaber")
    iban=$(pflicht_eingabe "💳 IBAN")
    bic=$(pflicht_eingabe "🏷️  BIC")

    echo "🧾 Welche steuerliche Identifikationsnummer soll auf Rechnungen stehen?"
    echo "   1) Steuernummer"
    echo "   2) Umsatzsteuer-Identifikationsnummer (USt-IdNr.)"
    while true; do
        read -r -p "Auswahl (1/2): " steuer_id_auswahl
        case "$steuer_id_auswahl" in
            1)
                steuer_id_typ="steuernummer"
                steuer_id_wert=$(pflicht_eingabe "🧾 Steuernummer")
                break
                ;;
            2)
                steuer_id_typ="ust_id"
                steuer_id_wert=$(pflicht_eingabe "🧾 Umsatzsteuer-Identifikationsnummer (USt-IdNr.)")
                break
                ;;
            *)
                echo "⚠️  Bitte 1 oder 2 eingeben."
                ;;
        esac
    done
    finanzamt=$(pflicht_eingabe "🏛️  Finanzamt")

    ku=$(ja_nein_eingabe "❓ Kleinunternehmerregelung nach § 19 UStG? (y/n)")
    if [ "$ku" = "y" ]; then
        kleinunternehmer=true
        mwst=""
    else
        kleinunternehmer=false
        mwst=$(prozent_eingabe "💰 Mehrwertsteuersatz in % (z. B. 19)")
    fi

    echo "⚠️  Hinweis: Für steuerkonforme Rechnungen muss eine Kopie gemäß § 14b UStG aufbewahrt werden."
    read -r -p "📧 BCC-Empfänger (optional, z.B. empfohlen zur Archivierung): " bcc
    read -r -p "📨 Sichtbarer Mail-Absendername (optional): " mail_from_name
    if [ -z "$bcc" ]; then
        echo "📌 Es wird empfohlen, eine BCC-Adresse zur revisionssicheren Archivierung anzugeben."
    fi

    mkdir -p data

    if [ ! -f "$CONFIG_WRITER" ]; then
        echo "❌ Konfigurationshelfer nicht gefunden: $CONFIG_WRITER"
        exit 1
    fi

    export SETUP_NAME="$name"
    export SETUP_FIRMA="$firma"
    export SETUP_STRASSE="$strasse"
    export SETUP_PLZ="$plz"
    export SETUP_ORT="$ort"
    export SETUP_TELEFON="$telefon"
    export SETUP_EMAIL="$email"
    export SETUP_WEBSITE="$website"
    export SETUP_BANKNAME="$bankname"
    export SETUP_KONTOINHABER="$kontoinhaber"
    export SETUP_IBAN="$iban"
    export SETUP_BIC="$bic"
    export SETUP_STEUER_ID_TYP="$steuer_id_typ"
    export SETUP_STEUER_ID_WERT="$steuer_id_wert"
    export SETUP_FINANZAMT="$finanzamt"
    export SETUP_KLEINUNTERNEHMER="$kleinunternehmer"
    export SETUP_MWST="$mwst"
    export SETUP_BCC="$bcc"
    export SETUP_MAIL_FROM_NAME="$mail_from_name"

    "$VENV_PYTHON" "$CONFIG_WRITER" "$KONFIG_PATH"
    unset SETUP_NAME SETUP_FIRMA SETUP_STRASSE SETUP_PLZ SETUP_ORT
    unset SETUP_TELEFON SETUP_EMAIL SETUP_WEBSITE SETUP_BANKNAME
    unset SETUP_KONTOINHABER SETUP_IBAN SETUP_BIC SETUP_STEUER_ID_TYP
    unset SETUP_STEUER_ID_WERT SETUP_FINANZAMT SETUP_KLEINUNTERNEHMER
    unset SETUP_MWST SETUP_BCC SETUP_MAIL_FROM_NAME

    echo ""
    echo "✅ konfiguration.json wurde gespeichert unter: $KONFIG_PATH"
else
    echo "🗂️  konfiguration.json ist bereits vorhanden – keine Änderungen vorgenommen."
fi

echo ""

# 6. Linux-Startskripte ausführbar machen
for start_script in rechnung_generieren.sh rechnung_cron.sh; do
    if [ -f "$start_script" ]; then
        chmod +x "$start_script"
    fi
done

echo "✅ Projekt ist bereit! Du kannst jetzt './rechnung_generieren.sh' ausführen."
