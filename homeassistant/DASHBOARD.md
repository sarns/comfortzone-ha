# Comfortzone-EX-Dashboard für Home Assistant

Das Dashboard besteht aus einer eigenen Karte `custom:comfortzone-card`
(`www/comfortzone/comfortzone-card.js`, eine Datei ohne Abhängigkeiten) und einer
Ansicht vom Typ `sections` mit Steuerung und Verlaufsdiagrammen.

Die Karte zeichnet das Schema als ein einziges SVG: Das Hintergrundbild
`comfortzone-ex-schema.png` und alle Messwert-Panels liegen im selben
Koordinatensystem (`viewBox` 1672 × 941). Text skaliert dadurch zusammen mit dem
Bild und kann sich auf keinem Bildschirm überlappen oder abgeschnitten werden.
Ist die **Karte selbst** schmaler als 900 px (z. B. auf dem iPhone), schaltet sie
per CSS-Container-Query auf ein Raster mit denselben Panels um. Es gibt nur noch
eine Konfiguration statt getrennter Desktop-, Tablet- und Mobilvarianten.

## Installation

1. Den Ordner `homeassistant/www/comfortzone` nach `/config/www/comfortzone` auf
   dem Home-Assistant-System kopieren (z. B. mit dem Add-on Studio Code Server).
2. Unter **Einstellungen → Dashboards → Drei-Punkte-Menü → Ressourcen** die
   Ressource `/local/comfortzone/comfortzone-card.js?v=1` als
   **JavaScript-Modul** hinzufügen.
3. Ein Dashboard anlegen, öffnen, **Dashboard bearbeiten → Drei-Punkte-Menü →
   Rohkonfigurationseditor** wählen und den Inhalt von
   `homeassistant/comfortzone-dashboard.yaml` einfügen.
4. Browser neu laden (Strg+Umschalt+R). In der iOS-/Android-App das Dashboard
   herunterziehen oder unter **Companion App → Debugging → Frontend-Cache
   zurücksetzen** wählen, sonst meldet die App „Konfigurationsfehler“.

Alternativ kann in einem vorhandenen Dashboard eine **Manuelle Karte** mit dem
Inhalt von `homeassistant/comfortzone-card.yaml` angelegt werden.

## Aktualisieren

Nach jeder Änderung an `comfortzone-card.js` die Datei erneut kopieren und die
Versionsnummer in der Ressourcen-URL erhöhen (`?v=2`, `?v=3`, …). Sonst laden
Browser und Apps weiterhin die alte Datei aus dem Cache.

## Funktionen

- Klick auf einen Messwert öffnet die Home-Assistant-Detailansicht mit Verlauf.
- Kompressor, Zusatzheizung und Warmwasser-Boost zeigen einen pulsierenden
  Statuspunkt. Die Zeile „Boost“ erscheint nur, wenn der Boost aktiv ist.
- „COP (live)“ im Kompressor-Panel wird von der Karte berechnet
  (Abgabe ÷ Aufnahme, nur bei mehr als 50 W Aufnahme) und stammt nicht vom Gerät.
- Ist der RS485-Bus offline, erscheint ein Hinweis „Werte sind veraltet“ und die
  Panels werden abgedunkelt.
- Die Darstellung enthält 41 der 43 Sensoren und Binärsensoren plus den
  berechneten COP. Die rein technischen Werte `last_decoded_frame_age` und
  `protocol_coverage` sind bewusst ausgeblendet; die Stellgrößen (Lüfterstufe,
  Sollwerte, Schalter) liegen in der Karte „Steuerung“.

## Konfiguration

```yaml
type: custom:comfortzone-card
entity_prefix: technikkeller_comfortzone_ex   # Standard
image: /local/comfortzone/comfortzone-ex-schema.png
compact_below: 900    # Kartenbreite in px, unterhalb derer das Raster erscheint
compact_image: true   # Schema-Bild über dem Raster anzeigen
panels:               # Panels verschieben, verbreitern oder ausblenden
  warmwasser: { x: 1250, y: 20 }
  energie: { hidden: true }
```

Panel-IDs: `aussen`, `raum`, `fortluft`, `kaeltekreis`, `warmwasser`,
`verdampfer`, `waermetauscher`, `heissgas`, `heizkreis`, `energie`, `laufzeit`,
`kompressor`, `zusatzheizung`, `leistung`, `status`. Die Standardpositionen und
Zeilen stehen in der Liste `PANELS` am Anfang von `comfortzone-card.js`.

Das Raster für schmale Karten benötigt iOS 16 bzw. einen aktuellen Browser
(CSS-Container-Queries).

## Hinweise

- Die kumulierten Energiezähler zeigen die Gesamtstände. Wochen- und
  Tagesverbrauch lassen sich mit Home-Assistant-Helfern vom Typ `utility_meter`
  ergänzen.
- Für die beiden Laufzeit-Entities in den jeweiligen Entity-Einstellungen die
  Anzeigeeinheit auf `h` setzen. Home Assistant rechnet die vom Gerät
  gelieferten Minuten für die Anzeige um; die Entity-IDs und deren Historie
  bleiben erhalten.
