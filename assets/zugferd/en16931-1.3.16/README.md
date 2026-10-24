# EN-16931-CII-Pruefregeln

Unveraenderte vorkompilierte XSLT aus dem offiziellen CEN/TC-434-Regelpaket
[validation-1.3.16](https://github.com/ConnectingEurope/eInvoicing-EN16931/releases/tag/validation-1.3.16).
Quelle, Archiv- und Dateipruefsummen stehen in `manifest.json`. Lizenz: EUPL 1.2,
beigefuegt als `LICENSE.txt`. Die Regeln werden lokal mit SaxonC-HE ueber die
Python-Anbindung ausgefuehrt. Java und Netzwerkzugriff sind nicht erforderlich.

Umfang: EN 16931 fuer UN/CEFACT CII D16B einschliesslich enthaltenen Codelisten.
Keine XRechnung-CIUS, keine vollstaendige PDF/A-Pruefung und keine eigenstaendige
ZUGFeRD-Profil-Schematron-Erweiterung. Ergaenzend prueft die Anwendung das
Factur-X-1.0.07-EN16931-XSD aus der festgelegten drafthorse-Version und erwartet
exakt `urn:cen.eu:en16931:2017` als Profilkennung.

Die Anwendung blockiert bei fehlgeschlagenen Regeln; als `warning` markierte
Hinweise blockieren nicht. Fehlermeldungen enthalten Regel-IDs, keine XML-Werte
oder Kundeninformationen. Regelupdates erfolgen bewusst im Quellcode mit Tests,
nicht automatisch waehrend eines Rechnungslaufs.
