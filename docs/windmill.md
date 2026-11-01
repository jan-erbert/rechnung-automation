# Windmill-Anbindung (optional)

Windmill führt dieselbe Python-Rechnungslogik wie CLI und Cron aus. Es ist kein
zweiter Rechnungsgenerator. Die [lokale Installation](installation.md)
funktioniert weiterhin ohne Windmill und ohne OpenBao.

## Worker und Definitionen vorbereiten

Der Worker benötigt einen Checkout dieser Projektversion, eine vorbereitete
Pythonumgebung mit PDF-Systembibliotheken sowie persistente Konfiguration,
Kunden, Versandverläufe und Archive. Ein Git-Pull installiert keine Pakete.
Optionale ZUGFeRD-Pakete müssen vor der Formatumstellung vorhanden sein.

Die [Generatoren](https://github.com/jan-erbert/rechnung-automation/blob/main/integrations/windmill/deployment.py) erstellen Definitionen,
starten aber keine Rechnung:

```python
from integrations.windmill.deployment import invoice_flow, script_definitions

scripts = script_definitions(
    project_root="/opt/rechnung-automation",
    python_executable="/opt/rechnung-automation/.venv/bin/python",
    allowed_domains=["example.invalid"],
)
flow = invoice_flow()
```

Projekt- und Pythonpfad sowie erlaubte Testdomains an die eigene Umgebung
anpassen. `allowed_domains=None` hebt die Domainbegrenzung auf; die Anwendung
hat keine fest eingebaute Testdomain. Die Vorgabe wird bei Bereitstellung gesetzt,
nicht als normales Kundenformularfeld angeboten.

Die Definitionen über die Windmill-API bereitstellen oder als Vorlage für eigene
Einstiege verwenden. Standard ist `f/rechnung/...`; bei einem anderen Ordner
Skriptpfade, Flowreferenzen und Ressourcen gemeinsam anpassen. `bridge.py` nutzt
`WM_WORKSPACE` und `WM_TOKEN` des Jobs sowie optional `BASE_INTERNAL_URL` für die
interne Windmill-Adresse. Ein Windmill-Python-Paket ist im Anwendungscode nicht
nötig. Ressourcen und Zeitpläne werden durch die Generatoren nicht angelegt.

| Skript unter `f/rechnung/` | Aufgabe |
| --- | --- |
| `validate` | Kundenstruktur prüfen, ohne Rechnung oder SMTP-Verbindung |
| `run_native` | Gemeinsamen Rechnungslauf als `dry-run` oder `send` ausführen |
| `report_failure` | Technischen Flowfehler an die konfigurierte Wartungsadresse melden |
| `customers` | Kunden und aktuelle Formularrevision anzeigen |
| `customer_create` | Neuen Kunden prüfen oder speichern |
| `customer_edit` | Kontakt oder zukünftige Konditionen prüfen oder speichern |

## SMTP und Secrets

Eine Ressource `f/rechnung/smtp` mit diesen Feldern bereitstellen. Die referenzierten
Variablen müssen als Secrets angelegt und für den Job zugänglich sein:

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

Optional liest derselbe Adapter Benutzer und Passwort aus OpenBao. Dafür die
SMTP-Ressource stattdessen so definieren:

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

Die referenzierte Ressource `f/rechnung/openbao` enthält beispielsweise:

```json
{
  "url": "https://vault.example.invalid",
  "mount": "projects",
  "path": "rechnung-automation/smtp",
  "role_id": "APPROLE-ID",
  "secret_id": "$var:f/rechnung/openbao_secret_id"
}
```

Der KV-v2-Datensatz enthält `user` und `password`. Eine eigene AppRole darf nur
diesen Datenpfad lesen und den eigenen Sitzungstoken widerrufen. Der Adapter
verlangt zertifikatsgeprüftes HTTPS, lehnt Redirects ab, akzeptiert Sitzungstokens
bis maximal fünf Minuten und widerruft sie nach dem Abruf. Die wiederverwendbare
AppRole-Secret-ID bleibt ein gesondert zu schützender und zu rotierender Zugang.
Keine Root-Tokens, Secretwerte in Ausgaben oder stillen Rückfälle auf `.env`.

Beim lokalen Einstieg bleiben `.env` oder vollständig gesetzte `MAIL_SERVER`,
`MAIL_PORT`, `MAIL_USER` und `MAIL_PASS` verwendbar. Der native Windmill-Versand
nutzt dagegen die ausgewählte Ressource; der Dry-Run liest keine SMTP-Secrets.

## Flow prüfen und aktivieren

Der mitgelieferte Flow prüft Eingaben, führt den Rechnungslauf einmal aus und
zeigt Laufzähler an. Erst mit Testkunden und begrenzten Empfängern prüfen:

1. Flow ohne Zeitplan im Standardmodus `dry-run` ausführen. Er rendert fällige
   PDFs im Speicher, versendet nichts und verändert keinen Rechnungszustand.
2. Einen bewusst freigegebenen Test mit `mode=send` und passender
   `smtp_resource` ausführen. Dieser Modus versendet, archiviert und schreibt
   den Versandverlauf fort. Empfänger einschließlich CC/BCC vorher prüfen.
3. Erst danach einen eigenen Zeitplan und die gewünschte Workerzuordnung setzen.
   Zeitzone von Scheduler und Anwendung abstimmen; die Anwendung nutzt lokale Zeit.

Es gibt keine automatische Wiederholung des Versand-Schritts. SMTP-Annahme und
lokales Speichern bilden keine gemeinsame Transaktion: Bei unklarem `pending`
vor erneutem Versand den [Versandstatus prüfen](betrieb.md).

Der Flow setzt im Hauptschritt `notify_errors=false` und verwendet stattdessen
`report_failure` als einzigen Fehlerhandler. Sonst könnten doppelte Fehlermails
entstehen. Dazu `config/notifications.yaml` mit eigener Wartungsadresse aktivieren
(siehe [Betrieb und Fehlerberichte](betrieb.md)). Direkte native
Sendeläufe melden standardmäßig selbst; Dry-Runs versenden keine Fehlerberichte.
Ein fehlgeschlagener Flow bleibt auch nach erfolgreicher Fehlermeldung fehlgeschlagen.

## Kunden verwalten und Umgebungen trennen

Kundenformulare erzeugen keine Rechnung. Zuerst `apply=false` für eine Vorschau
verwenden; erst `apply=true` speichert. Beim Bearbeiten zusätzlich die aktuelle
`expected_revision` aus der Vorschau übergeben. Veraltete Revisionen werden
abgewiesen. Kundenliste und Ergebnisse enthalten private Stammdaten.

[Kontaktnamen und Anreden](kunden.md) werden über `first_name`,
`last_name` und `salutation` ausdrücklich gepflegt.
Kontaktänderungen gelten für folgende Läufe; Konditionen ab einer zukünftigen
Abrechnungsgrenze. Bereits gespeicherte Rechnungen bleiben unverändert.
Wechsel von Abrechnungstyp oder Stundenzyklus sowie wechselnde Zusatzleistungen
in rückwirkenden Stundenzeiträumen werden nicht automatisch umgesetzt.

`runtime.new_customer()` kann `archive_directory` übernehmen. Der Betreiber muss
diesen Ordner vorab bereitstellen; die portable Kundenanlage legt ihn nicht an.
Für Prod und Dev getrennte Checkouts, private Daten, Historien, Archive und
Ressourcen verwenden. Gemeinsam genutzte Worker allein sind keine Isolation.
Vor Schemaänderung oder Rollback Code und private Daten gemeinsam prüfen und
sichern; Details unter [Kundendaten](kunden.md) und
[Betrieb](betrieb.md).
