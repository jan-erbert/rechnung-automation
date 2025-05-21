#!/bin/bash

echo "🔧 Starte Einrichtung der virtuellen Umgebung..."

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
if [ -f "requirements.txt" ]; then
    echo "📦 Installiere Pakete aus requirements.txt..."
    .venv/bin/pip install -r requirements.txt
else
    echo "⚠️  Keine requirements.txt gefunden."
fi

# 4. Konfigurationsdatei erstellen
KONFIG_PATH="data/konfiguration.json"
if [ ! -f "$KONFIG_PATH" ]; then
    echo ""
    echo "🛠️  Konfigurationsdatei wird erstellt ($KONFIG_PATH)..."
    echo ""

    function pflicht_eingabe() {
        local prompt="$1"
        local eingabe=""
        while [ -z "$eingabe" ]; do
            read -p "$prompt: " eingabe
            if [ -z "$eingabe" ]; then
                echo "⚠️  Dieses Feld ist gesetzlich erforderlich, da Rechnungen gemäß § 14 UStG bestimmte Pflichtangaben enthalten müssen – z. B. vollständiger Name, Adresse, Steuernummer oder Kontoverbindung."
            fi
        done
        echo "$eingabe"
    }

    # Eingaben
    name=$(pflicht_eingabe "👤 Dein Name (z. B. Jan Erbert)")
    firma=$(pflicht_eingabe "🏢 Firmenname (z. B. Web Development)")
    strasse=$(pflicht_eingabe "📍 Straße und Hausnummer")
    plz=$(pflicht_eingabe "📮 PLZ")
    ort=$(pflicht_eingabe "🌆 Ort")
    telefon=$(pflicht_eingabe "📞 Telefonnummer")
    email=$(pflicht_eingabe "📧 E-Mail-Adresse")
    read -p "🔗 Webseite (optional): " website

    bankname=$(pflicht_eingabe "🏦 Bankname")
    kontoinhaber=$(pflicht_eingabe "👤 Kontoinhaber")
    iban=$(pflicht_eingabe "💳 IBAN")
    bic=$(pflicht_eingabe "🏷️  BIC")

    steuernummer=$(pflicht_eingabe "🧾 Steuernummer")
    finanzamt=$(pflicht_eingabe "🏛️  Finanzamt")

    read -p "❓ Kleinunternehmerregelung nach § 19 UStG? (y/n): " ku
    if [ "$ku" == "y" ]; then
        kleinunternehmer=true
    else
        kleinunternehmer=false
        mwst=$(pflicht_eingabe "💰 Mehrwertsteuersatz in % (z. B. 19)")
    fi

    echo "⚠️  Hinweis: Für steuerkonforme Rechnungen muss eine Kopie gemäß § 14b UStG aufbewahrt werden."
    read -p "📧 BCC-Empfänger (optional, z.B. empfohlen zur Archivierung): " bcc
    if [ -z "$bcc" ]; then
        echo "📌 Es wird empfohlen, eine BCC-Adresse zur revisionssicheren Archivierung anzugeben."
    fi

    # data/-Ordner sicherstellen
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
    "steuernummer": "$steuernummer",
    "finanzamt": "$finanzamt",
    "kleinunternehmer": $kleinunternehmer$( [ "$kleinunternehmer" = false ] && echo ", \"mehrwertsteuer_prozent\": $mwst" )
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

# 5. Start-Skript für Linux/macOS erzeugen
START_SCRIPT="start-rechnung.sh"
if [ ! -f "$START_SCRIPT" ]; then
    cat > "$START_SCRIPT" <<EOF
#!/bin/bash
source .venv/bin/activate
python3 main.py
EOF
    chmod +x "$START_SCRIPT"
    echo "🚀 $START_SCRIPT wurde erstellt."
fi

echo "✅ Projekt ist bereit! Du kannst jetzt 'main.py' ausführen."