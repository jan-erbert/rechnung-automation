#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"

cd "$PROJECT_ROOT" || exit 1

echo "🔧 Starte Einrichtung der virtuellen Umgebung..."

if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ python3 wurde nicht gefunden. Bitte installiere Python 3."
    exit 1
fi

# 1. Virtuelle Umgebung erstellen
if [ ! -d ".venv" ]; then
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
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "📦 Installiere Pakete aus $REQUIREMENTS_FILE..."
    .venv/bin/python -m pip install -r "$REQUIREMENTS_FILE"
else
    echo "⚠️  Keine requirements.txt gefunden unter: $REQUIREMENTS_FILE"
fi

# 4. Env-Datei erstellen
ENV_PATH=".env"
if [ ! -f "$ENV_PATH" ]; then
    echo ""
    echo "📧 Mail-Umgebung wird erstellt ($ENV_PATH)..."
    echo ""

    read -r -p "SMTP-Server: " mail_server
    read -r -p "SMTP-Port (z. B. 587): " mail_port
    while ! [[ "$mail_port" =~ ^[0-9]+$ ]]; do
        echo "⚠️  Bitte eine numerische Portnummer eingeben."
        read -r -p "SMTP-Port (z. B. 587): " mail_port
    done
    read -r -p "SMTP-Benutzer: " mail_user
    read -r -s -p "SMTP-Passwort: " mail_pass
    echo ""

    old_umask="$(umask)"
    umask 077
    cat > "$ENV_PATH" <<EOF
MAIL_SERVER=$mail_server
MAIL_PORT=$mail_port
MAIL_USER=$mail_user
MAIL_PASS=$mail_pass
EOF
    umask "$old_umask"

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

    function pflicht_eingabe() {
        local prompt="$1"
        local eingabe=""
        while [ -z "$eingabe" ]; do
            read -r -p "$prompt: " eingabe
            if [ -z "$eingabe" ]; then
                echo "⚠️  Dieses Feld ist gesetzlich erforderlich."
            fi
        done
        echo "$eingabe"
    }

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

    wirtschafts_id=$(pflicht_eingabe "🧾 Wirtschafts-Identifikationsnummer (W-IdNr.)")
    finanzamt=$(pflicht_eingabe "🏛️  Finanzamt")

    read -r -p "❓ Kleinunternehmerregelung nach § 19 UStG? (y/n): " ku
    if [ "$ku" == "y" ]; then
        kleinunternehmer=true
        mwst_part=""
    else
        kleinunternehmer=false
        mwst=$(pflicht_eingabe "💰 Mehrwertsteuersatz in % (z. B. 19)")
        mwst_part=", \"mehrwertsteuer_prozent\": $mwst"
    fi

    echo "⚠️  Hinweis: Für steuerkonforme Rechnungen muss eine Kopie gemäß § 14b UStG aufbewahrt werden."
    read -r -p "📧 BCC-Empfänger (optional, z.B. empfohlen zur Archivierung): " bcc
    if [ -z "$bcc" ]; then
        echo "📌 Es wird empfohlen, eine BCC-Adresse zur revisionssicheren Archivierung anzugeben."
    fi

    mkdir -p data

    # JSON schreiben
    cat > "$KONFIG_PATH" <<EOF
{
  "absender": {
    "name": "$name",
    "firma": "$firma",
    "straße": "$strasse",
    "plz": "$plz",
    "ort": "$ort",
    "telefon": "$telefon",
    "email": "$email",
    "website": "$website"
  },
  "bank": {
    "bankname": "$bankname",
    "kontoinhaber": "$kontoinhaber",
    "iban": "$iban",
    "bic": "$bic"
  },
  "finanzen": {
    "wirtschafts_id": "$wirtschafts_id",
    "finanzamt": "$finanzamt",
    "kleinunternehmer": $kleinunternehmer$mwst_part
  },
  "mail": {
    "bcc": "$bcc"
  }
}
EOF

    echo ""
    echo "✅ konfiguration.json wurde gespeichert unter: $KONFIG_PATH"
else
    echo "🗂️  konfiguration.json ist bereits vorhanden – keine Änderungen vorgenommen."
fi

echo ""

# 6. Start-Skript für Linux/macOS erzeugen
START_SCRIPT="start-rechnung.sh"
if [ ! -f "$START_SCRIPT" ]; then
    cat > "$START_SCRIPT" <<EOF
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
"\$SCRIPT_DIR/.venv/bin/python" "\$SCRIPT_DIR/src/main.py"
EOF
    chmod +x "$START_SCRIPT"
    echo "🚀 $START_SCRIPT wurde erstellt."
fi

echo "✅ Projekt ist bereit! Du kannst jetzt './start-rechnung.sh' ausführen."
