# Capture-Protokoll (Vorlage)

Vorlage zum Ausfüllen direkt an der Wärmepumpe während eines Mitschnitts.
Hintergrund: `doc/plan-protokollerweiterung.md`, Phase 1.

Datum: ____________  Mitschnitt-Datei: `captures/________________.log.gz`

## Checkliste vor dem Start

- [ ] Handyuhr mit Netzzeit synchronisieren (automatische Zeit aus- und wieder
      einschalten); Abweichung zum Raspberry Pi prüfen (`date` per SSH).
- [ ] `raw_frame_logging: true` setzen und Firmware per OTA installieren.
- [ ] Mitschnitt auf dem Raspberry Pi starten (am besten in `tmux`/`screen`):

  ```bash
  python3 tools/capture_usb_serial.py /dev/ttyACM0 --seconds 43200 \
    --timestamp-lines --output captures/comfortzone-<name>-<datum>.log.gz
  ```

- [ ] Prüfen, dass die Datei wächst (`ls -l captures/`).
- [ ] Beenden mit Strg+C (oder `kill`), nicht die SSH-Sitzung hart trennen.

## Ablaufprotokoll

Jede Aktion mit der Uhrzeit vom Handy eintragen, bei Start/Ende von
Legionellen und Extra Warmwasser sekundengenau.

| Uhrzeit (hh:mm:ss) | Aktion / Menüseite | Foto (Dateiname) | Bemerkung |
|---|---|---|---|
| | Normale Ansicht, Leerlauf | | |
| | Erweiterte Ansicht Seite 1, Leerlauf | | |
| | Erweiterte Ansicht Seite 2, Leerlauf | | |
| | Erweiterte Ansicht Seite 3 (weitere Seiten ergänzen), Leerlauf | | |
| | Normale Ansicht, Heizen | | |
| | Erweiterte Ansicht Seite 1, Heizen | | |
| | Erweiterte Ansicht Seite 2, Heizen | | |
| | Erweiterte Ansicht Seite 3, Heizen | | |
| | Normale Ansicht, Warmwasser | | |
| | Erweiterte Ansicht Seite 1, Warmwasser | | |
| | Erweiterte Ansicht Seite 2, Warmwasser | | |
| | Erweiterte Ansicht Seite 3, Warmwasser | | |
| | Legionellen manuell GESTARTET (sekundengenau) | | |
| | Legionellen-Lauf: Zwischenstand / Foto | | |
| | Legionellen-Lauf BEENDET (Ende am Display) | | |
| | Legionellen abgebrochen (nur falls gefahrlos möglich) | | |
| | Extra Warmwasser EIN | | |
| | Extra Warmwasser AUS (ca. 1 min nach EIN) | | |
| | WW-Soll um +0,5 K erhöht (alter Wert -> neuer Wert) | | |
| | WW-Soll zurück auf Ausgangswert | | |
| | | | |
| | | | |

Bei jeder Seite vermerken, ob sie neu geöffnet wurde: Das Bedienteil fragt
beim Öffnen vermutlich zusätzliche Register ab.

## Fotowerte (`fotowerte.csv`)

Die auf den Fotos angezeigten Werte werden danach abgetippt. Sie sind die
Eingabe für `tools/correlate_photos.py`, das sie mit den Registern im
Mitschnitt abgleicht.

Format:

- Kopfzeile genau: `timestamp,label,value,unit`
- `timestamp`: ISO 8601 in Ortszeit, z. B. `2026-11-02T09:12:05`
  (Zeitzone optional, es wird Ortszeit angenommen). Die Zeit stammt aus dem
  Ablaufprotokoll bzw. den Foto-Metadaten.
- `label`: Bezeichnung des Werts wie am Display (z. B. `Außentemperatur`).
- `value`: Dezimalzahl mit Punkt als Trenner (`21.5`, nicht `21,5`).
- `unit`: Einheit (`C`, `K`, `%`, `W`, `h`, `l/min`, ...), leer erlaubt.
- Keine Kommas in `label`; keine Anführungszeichen nötig.

Ein Foto erzeugt viele Zeilen: pro angezeigtem Wert eine Zeile, alle mit
demselben Zeitstempel.

```csv
timestamp,label,value,unit
2026-11-02T09:12:05,Außentemperatur,8.4,C
2026-11-02T09:12:05,Warmwasser Ist,48.5,C
2026-11-02T09:12:05,Warmwasser Soll,50.0,C
2026-11-02T09:12:05,Verdichter Drehzahl,45,%
2026-11-02T09:12:40,Vorlauf,34.2,C
2026-11-02T09:12:40,Rücklauf,29.8,C
```
