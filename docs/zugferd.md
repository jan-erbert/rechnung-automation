# Optionale ZUGFeRD-Ausgabe

Standardmäßig erzeugt das Tool normale PDFs. Optional entsteht eine ZUGFeRD-PDF
im Profil **EN 16931**: Das sichtbare Rechnungsdokument bleibt eine PDF, die
strukturierten Rechnungsdaten sind als `factur-x.xml` darin eingebettet.
Es wird nicht automatisch eine zweite XML-Datei an die E-Mail angehängt.

PDF-Betrachter mit Unterstützung für eingebettete Dateien zeigen die XML als
Anlage im Dokument. Rechnungssoftware kann sie direkt auslesen; nicht jeder
Browser-PDF-Betrachter zeigt diese Dateianlagen an. Das Fehlen einer zweiten
Mailanlage ist deshalb kein Fehler.

## Zusatzpakete installieren

Die vorhandene WeasyPrint-Installation bleibt erforderlich. In einer bestehenden
Installation aus dem Projektverzeichnis:

```bash
# Linux/macOS
.venv/bin/python tools/install_zugferd.py --install
.venv/bin/python tools/install_zugferd.py
```

```powershell
# Windows
.venv\Scripts\python.exe tools/install_zugferd.py --install
.venv\Scripts\python.exe tools/install_zugferd.py
```

Für eine neue Einrichtung gibt es `./install/install.sh --zugferd` oder
`./install/install.ps1 -Zugferd`. Ohne Schalter bleibt die normale Installation
unverändert. Der Zusatzinstaller installiert festgelegte Python-Pakete in den
aufgerufenen Interpreter; ohne `--install` prüft er nur die Voraussetzungen.
Er aktiviert das Ausgabeformat nicht und ändert keinen Rechnungszustand.

Es ist kein Java und kein Zusatzserver nötig. Einige Pakete enthalten native
Bibliotheken; die Lösung ist daher keine ausschließlich reine Python-Laufzeit.
Die gepinnten Wheels decken CPython 3.10/3.12 auf Linux x86_64/ARM64 mit glibc ab
2.24, Windows x86_64 und macOS Intel/Apple Silicon ab. Windows ARM und Alpine/musl
sind mit diesen Paketen nicht abgedeckt. Es werden nur fertige Wheels installiert.

## Format bewusst wählen

In `config/settings.yaml` oder als privater Vorrang in `config/invoice.yaml`:

```yaml
pdf:
  format: zugferd
```

`format: pdf` wählt die normale PDF-Ausgabe. Installation und Formatwahl sind
getrennte Schritte. Vor einer automatischen Umstellung die Zusatzpakete auch im
Worker bereitstellen und mit fiktiven Daten testen.

## Was lokal geprüft wird

| Komponente | Aufgabe |
| --- | --- |
| WeasyPrint | PDF/A-3-Ausgabe und XML-Einbettung |
| Drafthorse | CII-XML aus strukturierten Rechnungsdaten |
| lxml | XML-Schema gegen das mitgelieferte Profil-XSD |
| SaxonC-HE | Mitgelieferte EN-16931-Geschäftsregeln |
| pypdf | Extrahierbare XML und Zuordnung im fertigen Dokument |

Positionen und Summen werden aus strukturierten Zahlen übernommen, nicht aus
formatierten Texten zurückgelesen. Fehlerhafte Daten, fehlende Pakete oder
gescheiterte Prüfungen blockieren die betroffene Rechnung. Es gibt keinen stillen
Rückfall auf eine normale PDF, keine Paketinstallation beim Rechnungslauf und
keinen Rechnungsupload an einen externen Dienst.

Die Ausgabe verwendet EUR und unterstützt die implementierten normalen
Umsatzsteuer- und Kleinunternehmerfälle. Länder werden über `sender.country_code`
und `contact.country_code` gepflegt, standardmäßig `DE`. Andere Steuerfälle ohne
definierte Abbildung werden nicht pauschal unterstützt. Dies ist keine separate
XRechnung-Ausgabe und kein unabhängiger universeller PDF/A-Validator.

Paketversionen stehen in [requirements-zugferd.txt](https://github.com/jan-erbert/rechnung-automation/blob/main/install/requirements-zugferd.txt).
Lizenzen und Herkunft: [THIRD_PARTY_NOTICES.md](https://github.com/jan-erbert/rechnung-automation/blob/main/THIRD_PARTY_NOTICES.md).
Die [Entwicklungsanleitung](entwicklung.md) beschreibt die isolierten PDF/XML-Tests.
