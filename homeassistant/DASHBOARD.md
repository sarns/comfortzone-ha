# Comfortzone-EX-Dashboard für Home Assistant

Das Dashboard verwendet nur die eingebaute Home-Assistant-Karte `picture-elements`.
Es werden keine zusätzlichen Frontend-Erweiterungen benötigt.

## Installation

1. Den Ordner `homeassistant/www/comfortzone` nach
   `/config/www/comfortzone` auf dem Home-Assistant-System kopieren.
2. Home Assistant neu laden oder den Browser-Cache aktualisieren. Das Bild ist
   danach unter `/local/comfortzone/comfortzone-ex-schema.png` erreichbar.
3. Unter **Einstellungen → Dashboards** ein neues Dashboard anlegen.
4. Das Dashboard öffnen, **Dashboard bearbeiten → Drei-Punkte-Menü →
   Rohkonfigurationseditor** wählen.
5. Den Inhalt von `homeassistant/comfortzone-dashboard.yaml` einfügen und
   speichern.

Die Ansicht verwendet den Typ `panel` und wählt über native
Bildschirmbedingungen automatisch eine Darstellung aus:

- ab 1400 px: vollständiges Desktop-Schema
- 600–1399 px: vereinfachtes Tablet-Schema mit zweispaltigen Detailkarten
- bis 599 px: iPhone-Ansicht mit Bild, Schnellübersicht und einspaltigen Listen

Home Assistant zeigt bedingte Karten während des Bearbeitens immer an. Die
responsive Auswahl deshalb nach dem Beenden des Bearbeitungsmodus prüfen.

Alternativ kann in einem vorhandenen Dashboard eine **Manuelle Karte** angelegt
und dort der Inhalt von `homeassistant/comfortzone-card.yaml` eingefügt werden.
Diese Karten-Datei beginnt direkt mit `type: picture-elements`; die vollständige
Dashboard-Datei beginnt dagegen mit `title:` und `views:`.

Ein Klick auf einen Messwert öffnet dessen Home-Assistant-Detailansicht mit dem
Verlauf. Die Darstellung enthält 25 der 27 exportierten Entities. Die rein
technischen Werte `last_decoded_frame_age` und `protocol_coverage` sind bewusst
ausgeblendet. Live-Werte liegen direkt bei ihren Bauteilen; Energie, Laufzeiten
und der RS485-Status stehen im freien unteren Bildbereich.

## Hinweise

- Die Desktop-, Tablet- und Mobilkarten liegen getrennt vor und werden mit
  `tools/generate_ha_dashboard.py` zur vollständigen Konfiguration kombiniert.
- Die kumulierten Energiezähler zeigen zunächst die Gesamtstände. Wochen- und
  Tagesverbrauch lassen sich anschließend mit Home-Assistant-Helfern vom Typ
  `utility_meter` ergänzen.
- Für die beiden Laufzeit-Entities in den jeweiligen Entity-Einstellungen die
  Anzeigeeinheit auf `h` und die Anzeigepräzision auf eine Nachkommastelle
  setzen. Home Assistant rechnet die vom Gerät gelieferten Minuten für die
  Anzeige um; die Entity-IDs und deren Historie bleiben erhalten.
