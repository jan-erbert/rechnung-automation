# Kunden und Abrechnung

Jeder Kunde hat eine YAML-Datei unter `customers/`. Die stabile `id` verbindet
Kundenakte, Stunden und Versandverlauf. Sie sollte dem Dateinamen entsprechen
und nach Beginn der Abrechnung nicht geändert werden.
Vollständige Vorlage: [customer.sample.yaml](https://github.com/jan-erbert/rechnung-automation/blob/main/sample/customer.sample.yaml).

## Name und Anrede ausdrücklich pflegen

```yaml
contact:
  first_name: Erika
  last_name: Musterfrau
  salutation: frau
```

Dies ist nur der Kontaktausschnitt. Alle drei Felder sind Pflichtfelder. Die
Anwendung errät weder Geschlecht noch Anrede aus dem Vornamen.

| `salutation` | Mailanrede | Benötigte Namen |
| --- | --- | --- |
| `frau` | Sehr geehrte Frau Musterfrau, | Nachname |
| `herr` | Sehr geehrter Herr Mustermann, | Nachname |
| `neutral` | Guten Tag Erika Musterfrau, | Mindestens ein Namensfeld |
| `organisation` | Sehr geehrte Damen und Herren, | Beide Namen dürfen leer sein |

Im PDF-Adressblock erscheint der vollständige Kontaktname ohne „Herr“/„Frau“.
Mehrteilige Nachnamen vollständig als `last_name` speichern; Titel und Anrede
nicht in Namensfelder mischen. Firmenname und Anschrift stehen in den weiteren
Kontaktfeldern, `email` ist der Empfänger und `cc` eine optionale Liste.

**Umstellung:** Das alte `contact.name` entfällt. Vor einem Update bestehende
Akten bewusst in `first_name`, `last_name` und `salutation` aufteilen und das alte
Feld entfernen. Es gibt keine automatische Zerlegung. Historische PDF-Dateien
und Versandverläufe werden dadurch nicht umgeschrieben.

## Kunden anlegen und ändern

In der aktivierten Projektumgebung:

```bash
python tools/create_customer.py
```

Das Werkzeug speichert eine Kundenakte, erzeugt jedoch keine Rechnung. Alternativ
YAML anhand der Vorlage pflegen oder die [Windmill-Formulare](windmill.md) nutzen.
`active: false` verhindert zukünftige Abrechnung; bereits erzeugte Rechnungen
bleiben erhalten. Nach Änderungen Setup und Fälligkeit kontrollieren.

Kontaktänderungen betreffen folgende E-Mails. Konditionsänderungen sollen für
zukünftige Leistungszeiträume gelten; dafür geplante Änderungen verwenden,
keine historischen Preise überschreiben.

## Leistungen und Fälligkeit

| Bereich | Wichtige Felder |
| --- | --- |
| `billing` | `invoice_prefix`, `cycle_months`, `due_days`, optional `end_month`, `invoice_date`, `one_time` |
| `main_service` | Beschreibung, `unit` (`month`, `hour`, `flat`), `unit_price` |
| `additional_services` | Liste mit `month`, `flat` oder `included` |
| `archive.directory` | Existierender Archivpfad oder `null` ohne PDF-Archivierung |

Der Zyklus ist eine positive ganze Zahl; die Zahlungsfrist eine nichtnegative
ganze Zahl (0 ist zulässig). Geldwerte sind
nichtnegative Dezimaltexte, etwa `"65.00"`. `invoice_date` hat das Format
`YYYY-MM-DD`, `end_month` das Format `YYYY-MM`.

Ein aktiver Kunde ohne abgeschlossenen Verlauf kann **bereits beim nächsten Lauf**
fällig sein. Bei wiederkehrenden Kunden werden Zyklus und letzter abgeschlossener
Abrechnungsmonat berücksichtigt. Ein bereits abgeschlossener Monat wird nicht
nochmals versendet. Der letzte Vertragsmonat kann eine abschließende Rechnung
auslösen; nach Vertragsende wird übersprungen. Einmalige Kunden werden nach einer
abgeschlossenen Rechnung nicht erneut regulär abgerechnet.
Offene oder unklare Zustände haben Vorrang; siehe [Versandstatus](betrieb.md).
Verlauf nicht löschen oder zurücksetzen, um einen erneuten Lauf zu erzwingen.

## Stunden pro Leistungsmonat

Datei `hours/2026-08.yaml`, beispielsweise:

```yaml
period: "2026-08"
customers:
  musterfirma:
    hours: 8.50
```

Stunden dürfen YAML-Zahlen oder Dezimaltexte sein, müssen nichtnegativ sein und
höchstens zwei Nachkommastellen haben. Ein monatlicher Lauf im September rechnet
abgeschlossene Auguststunden ab. Mehrmonatige Zyklen beziehen entsprechend mehrere
abgeschlossene Leistungsmonate ein.

Interaktiv werden fehlende Werte abgefragt und gespeichert. Im automatischen
Lauf bleibt die Rechnung mit `waiting_hours` offen; ein fehlender Wert bedeutet
nicht null Stunden. Ausdrücklich erfasste null Stunden können einen Zeitraum ohne
Rechnung abschließen. Offene ältere Zeiträume vor Fortsetzung prüfen.

## Zukünftige Konditionen

Für planbare Änderungen die gemeinsame Kundenverwaltung, etwa das
Windmill-Bearbeitungsformular, verwenden. Sie erzeugt `scheduled_changes`:

```yaml
scheduled_changes:
  - effective_from: "2026-12"
    changes:
      main_service:
        unit_price: "75.00"
```

Die Einträge müssen nach Wirksamkeitsmonat streng aufsteigend sein. Änderungen
an `billing` beschränken sich auf Zyklus, Zahlungsfrist und Vertragsende;
Haupt-/Zusatzleistungen werden anhand des Leistungszeitraums aufgelöst.
Unterschiedliche historische Stundensätze erscheinen als getrennte Monatspositionen.
Wechsel von Leistungstyp oder Stundenzyklus und widersprüchliche Zusatzleistungen
über Stundenzeiträume werden nicht stillschweigend umgesetzt.
Formularvorschau prüfen und erst danach speichern. Das Speichern einer
Konditionsänderung löst selbst keine Rechnung aus.
