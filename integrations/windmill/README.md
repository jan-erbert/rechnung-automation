# Optionale Windmill-Anbindung

Die normale CLI bleibt ohne Windmill und ohne OpenBao verwendbar:
interaktiv, `--non-interactive` fuer Cron und `--dry-run` fuer die Vorschau.
Die Integration verwendet dieselbe Rechnungslogik ueber
`main.run_application(...)`. Sie ist kein zweiter Rechnungsgenerator.

## Worker und Bereitstellung

Der Worker benoetigt einen Checkout dieser Projektversion, persistente private
Datenverzeichnisse sowie die normalen Python- und PDF-Abhaengigkeiten. Ein
Git-Update installiert keine geaenderten Bibliotheken. Ein geeignetes eigenes
Worker-Image oder eine vorbereitete virtuelle Pythonumgebung bleibt erforderlich.

`deployment.script_definitions(project_root, allowed_domains=None,
python_executable='python3')` erstellt die fuenf portablen Skriptdefinitionen.
Fuer eine virtuelle Umgebung deren absoluten Pythonpfad angeben. Die schlanken
Windmill-Skripte starten `bridge.py` in dieser Umgebung; benoetigt wird kein
Windmill-Python-Paket in der allgemeinen Anwendung. `deployment.invoice_flow()`
liefert den Flow als JSON-serialisierbares OpenFlow-Dokument.

Die Definitionen lassen sich ueber die Windmill-API bereitstellen oder als
Vorlage fuer die eigenen Einstiegsskripte verwenden. Der Workerpfad ist
konfigurierbar; dieses Repository enthaelt keine fest eingebauten NAS-Adressen.
Die mitgelieferten Pfade `f/rechnung/...` koennen fuer eine eigene Installation
gezielt angepasst werden. Zeitplaene werden nicht automatisch aktiviert.

Der Flow besteht aus Pruefung, einmaligem Rechnungslauf und Ergebnisanzeige.
Standardmodus ist `dry-run`. Der Modus `send` fuehrt den normalen
unbeaufsichtigten Versand mit Archiv- und Historienpflege aus. Es gibt keine
automatische Wiederholung des Versand-Schritts. SMTP-Annahme und lokale
Zustandsschreibung sind keine gemeinsame Transaktion; unklaren Versandstatus
vor einer Wiederholung pruefen. Die bestehende Rechnungslauf-Sperre bleibt aktiv.

## Ressourcen und Secrets

Fuer Windmill-interne Secrets kann eine SMTP-Ressource folgendes Schema nutzen:

```json
{
  "server": "smtp.example.invalid",
  "port": 587,
  "security": "starttls",
  "timeout": 30,
  "secret_provider": "windmill",
  "user": "$var:f/rechnung/smtp_user",
  "password": "$var:f/rechnung/smtp_password"
}
```

Alternativ verweist dieselbe Ressource auf einen eigenen OpenBao-Abruf:

```json
{
  "server": "smtp.example.invalid",
  "port": 587,
  "security": "starttls",
  "timeout": 30,
  "secret_provider": "openbao",
  "openbao_resource": "f/rechnung/openbao"
}
```

Die referenzierte OpenBao-Ressource enthaelt `url` (HTTPS), `mount`, `path`,
`role_id` und `secret_id`. `secret_id` muss als Windmill-Secretreferenz
hinterlegt werden. Der KV-v2-Datensatz enthaelt `user` und `password`.
Eine eigene AppRole darf ausschliesslich diesen Datenpfad lesen und ihren
Sitzungstoken ueber `auth/token/revoke-self` widerrufen. Kein Administrator-
oder Root-Token fuer Rechnungsjobs.

Der Adapter akzeptiert nur TLS-geprueftes HTTPS, lehnt Redirects ab, verlangt
Sitzungstokens mit maximal fuenf Minuten Laufzeit und widerruft sie nach dem
Abruf. Fehler fuehren zum Abbruch, ohne Rueckgriff auf eine lokale `.env`.
Die AppRole-Secret-ID bleibt ein gesondert zu schuetzender und zu rotierender
Anmeldezugang. Zugangsdaten duerfen nicht als Flow-Ausgabe oder Log erscheinen.
Der Dry-Run verwendet Dummy-SMTP und liest keine Secrets.

Der lokale Einstieg laedt weiterhin `.env`; vollstaendige `MAIL_SERVER`,
`MAIL_PORT`, `MAIL_USER` und `MAIL_PASS` aus der Prozessumgebung funktionieren
auch ohne diese Datei. Ein direkt uebergebenes Mailconfig-Objekt hat beim
Python-API-Einstieg Vorrang. Die Umgebungsvariablen werden dabei nicht veraendert.

## Kundenverwaltung

Die Formulare `customers`, `customer_create` und `customer_edit` verwenden die
Funktionen aus `src/customer_management.py`. Sie erzeugen keine Rechnung und
versenden keine Mail. Standard ist Vorschau (`apply=false`). Eine Aenderung
wird erst mit `apply=true` gespeichert; beim Bearbeiten muss die `revision`
aus der Vorschau erneut uebergeben werden. Veraltete Formulare werden abgewiesen.
Die erste Oberflaeche besteht aus nativen Windmill-Formularen, nicht aus einer
separaten umfangreichen Verwaltungs-App. Kundenliste und Form-Ergebnisse
enthalten private Stammdaten und gehoeren ausschliesslich in berechtigte Ordner.

Kontaktdaten gelten fuer folgende Laeufe. Preise und Konditionen werden fuer
eine zukuenftige Abrechnungsgrenze geplant und in `scheduled_changes`
gespeichert. Alte Rechnungsdateien und Rechnungshistorien werden dabei nicht
geaendert. Bei vorausbezahlten Quartalen ist kein Preiswechsel mitten in einer
bereits abgerechneten Periode moeglich. Stundenpreise richten sich nach dem
Leistungsmonat, auch bei spaeterer Rechnung. Unterschiedliche Stundensaetze
werden als getrennte Monatspositionen und in der neuen Historie dokumentiert.

Wechsel des Abrechnungstyps und Zykluswechsel bei Stundenkunden werden in der
Verwaltung ausdruecklich abgewiesen. Wechselnde Zusatzleistungen innerhalb eines
rueckwirkenden Stundenzeitraums erfordern ebenfalls eine gesonderte Pruefung.
Diese Faelle werden nicht still mit einem falschen Betrag abgerechnet.

Kundenanlage und Aenderung verwenden dieselbe Betriebssystem-Sperre wie der
Rechnungslauf sowie den atomaren YAML-Writer. Ein optionales `allowed_domains`
in der Bereitstellung begrenzt To, CC und BCC beim Lauf und die Kundenadressen
beim Speichern. Die allgemeine Anwendung hat keine feste Test-Maildomain.
Die Grenze wird vom Deployer festgelegt und ist kein normales Formulareingabefeld.

Vor der Nutzung neuer Kundenschemafelder alle verwendeten Anwendungseinstiege
auf diese Version aktualisieren. Aeltere Releases kennen `scheduled_changes`
und `change_history` nicht. Ein Rollback muss auch diese privaten Daten
beruecksichtigen; vor der Umstellung geschuetzte Sicherungen anlegen.
