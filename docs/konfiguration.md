# Konfiguration und Gestaltung

## Welche Daten liegen wo?

| Datei/Verzeichnis | Inhalt | In Git? |
| --- | --- | --- |
| `config/settings.yaml` | Technische Pfade, Design, Logging, SMTP-Verhalten | Ja |
| `config/invoice.yaml` | Absender, Bank, Steuern, sichtbare Mailangaben | Nein |
| `config/notifications.yaml` | Technische Wartungsadresse | Nein |
| `.env` | Lokale SMTP-Zugangsdaten | Nein |
| `customers/<id>.yaml` | Kunden und Verträge | Nein |
| `hours/YYYY-MM.yaml`, `data/` | Stunden und erzeugter Versandverlauf | Nein |
| `templates/`, `sample/` | HTML-Vorlagen und fiktive Beispiele | Ja |

Vollständige Beispiele: [Settings](https://github.com/jan-erbert/rechnung-automation/blob/main/sample/settings.sample.yaml),
[Rechnungskonfiguration](https://github.com/jan-erbert/rechnung-automation/blob/main/sample/invoice.sample.yaml),
[Kunden](https://github.com/jan-erbert/rechnung-automation/blob/main/sample/customer.sample.yaml) und [Fehleradresse](https://github.com/jan-erbert/rechnung-automation/blob/main/sample/notifications.sample.yaml).
Unbekannte oder doppelte YAML-Schlüssel werden abgewiesen.

## Absender, Bank und Steuern

`config/invoice.yaml` enthält `sender`, `bank`, `tax` und `mail`.
Absenderadresse, Kontoinhaber, IBAN/BIC und steuerliche Angaben vor dem ersten
Lauf kontrollieren. Geld- und Prozentwerte als Texte schreiben, etwa `"19.00"`;
die Anwendung rechnet mit `Decimal`. Postleitzahlen und Telefonnummern ebenfalls
als Texte pflegen, damit führende Nullen erhalten bleiben.

`tax.identifier_type` ist `tax_number` oder `vat_id`. `tax.small_business` und
`tax.vat_rate` müssen zum eigenen Fall passen. `tax.tax_office` enthält den
vollständigen Namen, etwa `Finanzamt Musterstadt`; der PDF-Footer gibt diesen
Wert ohne zusätzliches „Finanzamt:“-Präfix aus.

`mail.from_name` bestimmt den sichtbaren Absendernamen, `mail.bcc` die globale
Rechnungskopie. Kunden haben eigene Empfänger und optional CC. BCC ist keine
technische Fehleradresse; diese steht separat in [notifications.yaml](betrieb.md).

## Lokaler SMTP-Zugang

In `.env` nur die eigene Verbindung hinterlegen, beispielsweise:

```dotenv
MAIL_SERVER=smtp.example.invalid
MAIL_PORT=587
MAIL_USER=DEIN-SMTP-BENUTZER
MAIL_PASS=DEIN-SMTP-PASSWORT
```

`mail.security` in `config/settings.yaml` erlaubt `starttls` oder `ssl`.
Port und Server müssen zum Anbieter passen; Standardtimeout ist 30 Sekunden.
TLS-Zertifikat und Hostname werden vor Anmeldung und Versand geprüft.
Die vier Werte können alternativ vollständig als Prozessumgebung gesetzt sein.
Keine Zugangsdaten in Git, Tickets oder Logs übernehmen.

Die optionale [Windmill-Anbindung](windmill.md) verwendet Ressourcen und bei Bedarf
OpenBao anstelle der lokalen SMTP-Datei.

## Pfade, Logo und Vorlagen

`paths` in den Settings enthält Daten-, Kunden-, Stunden-, Template-, Bild- und
Backupverzeichnisse sowie den Pfad zur Rechnungskonfiguration. Der Archivpfad wird
pro Kunde unter `archive.directory` gesetzt. Bestehende, beschreibbare Pfade
verwenden; ein nicht zugängliches Archiv wird als Fehler gemeldet.

`branding.pdf_logo` und `branding.mail_logo` benennen getrennte Bilder unter
`paths.image_dir`. Vorgaben sind `sample_logo.png` und `mail_logo.png`, mit
Logo-Höhen 40 beziehungsweise 60. `header_title` und `header_subtitle` bieten
Ersatztexte bei fehlendem Logo. Eigene Bilder sind private Dateien.

Die tatsächlichen HTML-Dateien liegen unter `templates/`, Muster unter `sample/`.
Eigene Mailvorlagen verwenden `{{ mail_salutation }}` für die vollständige
Anrede einschließlich Komma. `{{ name }}` ist nur der vollständige Kontaktname.
Templateänderungen zunächst mit fiktiven Daten prüfen.

## Farben, Abstände und Symbole

PDF- und Mailtabellen teilen dieselben neutralen Voreinstellungen:

```yaml
design:
  tables:
    header_background: "#F1F3F5"
    total_background: "#EEF1F3"
    border_color: "#D9DEE3"
    header_text_color: "#303942"
    body_text_color: "#111827"
    row_background: "#FFFFFF"
```

Das Beispiel ist ein Ausschnitt; in bestehende Settings einfügen, nicht die ganze
Datei ersetzen. Alle Farben sind sechsstellige Hexwerte. Weitere Vorlagen stehen
unter [sample/design-presets.yaml](https://github.com/jan-erbert/rechnung-automation/blob/main/sample/design-presets.yaml).
`design.pdf` und `design.mail` enthalten getrennte Akzent- und Linkfarben.

`design.pdf_layout.margin_top_mm`, `margin_right_mm`, `margin_bottom_mm` und
`margin_left_mm` sind ganze Werte von 5 bis 30; Standard jeweils 15 mm.
Der untere Wert bestimmt den Abstand des Footers zur Papierkante; der
Inhaltsbereich reserviert weiterhin 40 mm für den Footer. Die Standardschrift
unter dessen Trennlinie ist 8,5 pt und in der HTML-Vorlage definiert.

Die dekorativen [Lucide-Symbole](https://github.com/jan-erbert/rechnung-automation/blob/main/assets/mail/README.md) sind lokale
Mailgrafiken. `branding.mail_icons_enabled: false` blendet sie aus.
`branding.mail_automation_notice_enabled: true` aktiviert den kleinen
Automatikhinweis; Standard ist `false`.
In privater Rechnungskonfiguration haben `mail.icons_enabled` und
`mail.automation_notice_enabled` jeweils Vorrang vor diesen Brandingwerten.

## Ausgabeformat und Dateinamen

`pdf.engine` ist `weasyprint`. `pdf.format` ist standardmäßig `pdf`; optional
`zugferd` nach [Zusatzinstallation](zugferd.md). Ein privates `pdf.format` in
`config/invoice.yaml` hat Vorrang vor dem versionierten Wert.

`file_naming.invoice_prefix` und `preview_prefix` stehen in den mitgelieferten
Settings auf `Rechnung` und `VORSCHAU`. Ohne diese optionalen Felder gelten
`Invoice` und `PREVIEW`. Präfixe dürfen Buchstaben, Zahlen, Binde- und
Unterstriche enthalten. Sie betreffen Dateinamen, nicht die fachliche Rechnungsnummer.
