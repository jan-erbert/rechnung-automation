# Optionale ZUGFeRD-Komponenten

Die normale PDF-Ausgabe bleibt unabhaengig von diesen optionalen Paketen.
Die Anwendung installiert sie nur nach ausdruecklicher Setup-Anforderung ueber
`install/requirements-zugferd.txt`. Paketquellen und Binaerdateien werden nicht in
dieses Repository kopiert. Java und Mustangproject werden nicht verwendet.

| Komponente | Festgelegte Version | Lizenz und Quelle | Verwendung |
|---|---|---|---|
| drafthorse | 2025.2.0 | [Apache-2.0](https://github.com/pretix/python-drafthorse/blob/master/LICENSE), [Quellcode](https://github.com/pretix/python-drafthorse) | CII-Rechnungsdaten und mitgeliefertes Profil-XSD |
| lxml | 6.1.3 | [BSD-3-Clause und Bibliothekshinweise](https://github.com/lxml/lxml/blob/master/LICENSES.txt), [Quellcode](https://github.com/lxml/lxml) | XML-Verarbeitung und XSD-Pruefung |
| pypdf | 6.21.2 | [BSD-3-Clause](https://github.com/py-pdf/pypdf/blob/main/LICENSE), [Quellcode](https://github.com/py-pdf/pypdf) | Kontrolle eingebetteter Rechnungsdaten |
| SaxonC-HE / saxonche | 13.1.0 | [MPL-2.0 und Saxonica-Lizenzhinweise](https://www.saxonica.com/license/terms.xml), [Produkt](https://www.saxonica.com/saxon-c/index.xml) | Lokale Ausfuehrung der offiziellen XSLT-Pruefregeln |
| EN16931 validation artefacts, CII | 1.3.16 | [EUPL-1.2](assets/zugferd/en16931-1.3.16/LICENSE.txt), [Quellcode](https://github.com/ConnectingEurope/eInvoicing-EN16931) | Unveraenderte offizielle Geschaeftsregeln |

Die mitgelieferten CEN-Regeln sind separat unter
`assets/zugferd/en16931-1.3.16/` mit Lizenz, Herkunft und Pruefsummen abgelegt.
Ihre Lizenz bleibt von der Lizenz unseres eigenen Anwendungscodes getrennt.
Aktualisierungen der Pakete oder Regeln sind bewusste Codeaenderungen mit Tests;
beim Rechnungsversand wird nichts heruntergeladen.

SaxonC-HE ist die quelloffene Home Edition; wir verwenden keinen kostenpflichtigen
PE-/EE-Modus. Es handelt sich um eine native Python-Erweiterung. Eine separate
Java-Installation ist nicht erforderlich.

Fuer die ueber pip bezogenen Pakete gelten deren eigene Lizenztexte und
gegebenenfalls weitere Hinweise fuer in Wheels enthaltene Bibliotheken, etwa
libxml2/libxslt in lxml. Diese Tabelle ersetzt solche Hinweise nicht. Wer eine
fertige Umgebung, Wheels oder ein Containerimage weitergibt, muss die
Lizenztexte, Copyrightvermerke und gegebenenfalls Quellcodehinweise dieser
konkreten Distribution erhalten und mitliefern. Der hier dokumentierte
Installationsweg ist kein pauschaler Nachweis fuer beliebige eigene
Weiterverteilungen oder veraenderte Drittkomponenten.

Die bestehende PDF-Engine WeasyPrint bleibt erhalten; ihre Lizenzinformationen
liegen beim regulaer installierten Paket. Die bereits vorhandenen lokalen
Lucide-Symbole behalten ihre ISC-Lizenz und die Hinweise unter `assets/mail/`.
