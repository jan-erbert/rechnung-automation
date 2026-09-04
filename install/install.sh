#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
CONFIG_WRITER="$SCRIPT_DIR/write_config.py"
ENV_WRITER="$SCRIPT_DIR/write_env.py"
LEGACY_MIGRATOR="$PROJECT_ROOT/tools/migrate_legacy_layout.py"
SETUP_CHECK="$PROJECT_ROOT/tools/check_setup.py"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

function read_required() {
    local prompt="$1"
    local value=""
    while [ -z "$value" ]; do
        read -r -p "$prompt: " value
        if [ -z "$value" ]; then
            echo "⚠️  Dieses Feld darf nicht leer sein." >&2
        fi
    done
    printf '%s' "$value"
}

function read_port() {
    local prompt="$1"
    local value=""
    while true; do
        value=$(read_required "$prompt")
        if [[ "$value" =~ ^[0-9]+$ ]] &&
            [ "$value" -gt 0 ] &&
            [ "$value" -le 65535 ]; then
            printf '%s' "$value"
            return
        fi
        echo "⚠️  Bitte einen Port zwischen 1 und 65535 eingeben." >&2
    done
}

function read_required_secret() {
    local prompt="$1"
    local value=""
    while [ -z "$value" ]; do
        read -r -s -p "$prompt: " value
        echo "" >&2
        if [ -z "$value" ]; then
            echo "⚠️  Dieses Feld darf nicht leer sein." >&2
        fi
    done
    printf '%s' "$value"
}

function read_percentage() {
    local prompt="$1"
    local value=""
    while true; do
        value=$(read_required "$prompt")
        if [[ "$value" =~ ^[0-9]+$ ]] && [ "$value" -le 100 ]; then
            printf '%s' "$value"
            return
        fi
        echo "⚠️  Bitte einen ganzzahligen Prozentsatz zwischen 0 und 100 eingeben." >&2
    done
}

function read_yes_no() {
    local prompt="$1"
    local value=""
    while true; do
        read -r -p "$prompt: " value
        case "${value,,}" in
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

# Vorhandene Installationen vor dem Anlegen neuer Konfiguration migrieren.
"$VENV_PYTHON" "$LEGACY_MIGRATOR"

# 4. Env-Datei erstellen
ENV_PATH=".env"
if [ ! -f "$ENV_PATH" ]; then
    echo ""
    echo "📧 Mail-Umgebung wird erstellt ($ENV_PATH)..."
    echo ""

    mail_server=$(read_required "SMTP-Server")
    mail_port=$(read_port "SMTP-Port (z. B. 587)")
    mail_user=$(read_required "SMTP-Benutzer")
    mail_pass=$(read_required_secret "SMTP-Passwort")

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
CONFIG_PATH="config/invoice.yaml"
if [ ! -f "$CONFIG_PATH" ]; then
    echo ""
    echo "🛠️  Konfigurationsdatei wird erstellt ($CONFIG_PATH)..."
    echo ""

    contact_name=$(read_required "👤 Dein Name (z. B. Jan Erbert)")
    company=$(read_required "🏢 Firmenname (z. B. Web Development)")
    street=$(read_required "📍 Straße und Hausnummer")
    postal_code=$(read_required "📮 PLZ")
    city=$(read_required "🌆 Ort")
    phone=$(read_required "📞 Telefonnummer")
    email=$(read_required "📧 E-Mail-Adresse")
    read -r -p "🔗 Webseite (optional): " website

    bank_name=$(read_required "🏦 Bankname")
    account_holder=$(read_required "👤 Kontoinhaber")
    iban=$(read_required "💳 IBAN")
    bic=$(read_required "🏷️  BIC")

    echo "🧾 Welche steuerliche Identifikationsnummer soll auf Rechnungen stehen?"
    echo "   1) Steuernummer"
    echo "   2) Umsatzsteuer-Identifikationsnummer (USt-IdNr.)"
    while true; do
        read -r -p "Auswahl (1/2): " tax_id_selection
        case "$tax_id_selection" in
            1)
                tax_identifier_type="tax_number"
                tax_identifier_value=$(read_required "🧾 Steuernummer")
                break
                ;;
            2)
                tax_identifier_type="vat_id"
                tax_identifier_value=$(read_required "🧾 Umsatzsteuer-Identifikationsnummer (USt-IdNr.)")
                break
                ;;
            *)
                echo "⚠️  Bitte 1 oder 2 eingeben."
                ;;
        esac
    done
    tax_office=$(read_required "🏛️  Finanzamt")

    small_business_choice=$(read_yes_no "❓ Kleinunternehmerregelung nach § 19 UStG? (y/n)")
    if [ "$small_business_choice" = "y" ]; then
        small_business=true
        vat_rate=""
    else
        small_business=false
        vat_rate=$(read_percentage "💰 Mehrwertsteuersatz in % (z. B. 19)")
    fi

    echo "⚠️  Hinweis: Für steuerkonforme Rechnungen muss eine Kopie gemäß § 14b UStG aufbewahrt werden."
    read -r -p "📧 BCC-Empfänger (optional, z.B. empfohlen zur Archivierung): " bcc
    read -r -p "📨 Sichtbarer Mail-Absendername (optional): " mail_from_name
    if [ -z "$bcc" ]; then
        echo "📌 Es wird empfohlen, eine BCC-Adresse zur revisionssicheren Archivierung anzugeben."
    fi

    mkdir -p config customers data hours

    if [ ! -f "$CONFIG_WRITER" ]; then
        echo "❌ Konfigurationshelfer nicht gefunden: $CONFIG_WRITER"
        exit 1
    fi

    export SETUP_CONTACT_NAME="$contact_name"
    export SETUP_COMPANY="$company"
    export SETUP_STREET="$street"
    export SETUP_POSTAL_CODE="$postal_code"
    export SETUP_CITY="$city"
    export SETUP_PHONE="$phone"
    export SETUP_EMAIL="$email"
    export SETUP_WEBSITE="$website"
    export SETUP_BANK_NAME="$bank_name"
    export SETUP_ACCOUNT_HOLDER="$account_holder"
    export SETUP_IBAN="$iban"
    export SETUP_BIC="$bic"
    export SETUP_TAX_IDENTIFIER_TYPE="$tax_identifier_type"
    export SETUP_TAX_IDENTIFIER_VALUE="$tax_identifier_value"
    export SETUP_TAX_OFFICE="$tax_office"
    export SETUP_SMALL_BUSINESS="$small_business"
    export SETUP_VAT_RATE="$vat_rate"
    export SETUP_BCC="$bcc"
    export SETUP_MAIL_FROM_NAME="$mail_from_name"

    "$VENV_PYTHON" "$CONFIG_WRITER" "$CONFIG_PATH"
    unset SETUP_CONTACT_NAME SETUP_COMPANY SETUP_STREET SETUP_POSTAL_CODE
    unset SETUP_CITY SETUP_PHONE SETUP_EMAIL SETUP_WEBSITE SETUP_BANK_NAME
    unset SETUP_ACCOUNT_HOLDER SETUP_IBAN SETUP_BIC SETUP_TAX_IDENTIFIER_TYPE
    unset SETUP_TAX_IDENTIFIER_VALUE SETUP_TAX_OFFICE SETUP_SMALL_BUSINESS
    unset SETUP_VAT_RATE SETUP_BCC SETUP_MAIL_FROM_NAME

    echo ""
    echo "✅ invoice.yaml wurde gespeichert unter: $CONFIG_PATH"
else
    echo "🗂️  invoice.yaml ist bereits vorhanden – keine Änderungen vorgenommen."
fi

mkdir -p customers data hours

echo "🔎 Pruefe die abgeschlossene Installation..."
"$VENV_PYTHON" "$SETUP_CHECK"

echo ""

# 6. Linux-Startskripte ausführbar machen
for start_script in generate_invoices.sh invoice_cron.sh; do
    if [ -f "$start_script" ]; then
        chmod +x "$start_script"
    fi
done

echo "✅ Projekt ist bereit! Du kannst jetzt './generate_invoices.sh' ausführen."
