# Plan: Protokollerweiterung (Messwerte, manueller Legionellen-Start)

Stand: 2026-10-30

## Ziele

1. Weitere Messwerte aus der erweiterten Ansicht des Bedienteils dekodieren und
   in Home Assistant veröffentlichen.
2. Die provisorische Zuordnung des Heizungsdurchflusses im Heizbetrieb
   bestätigen.
3. Die **manuelle Legionellenfunktion** aus der Ferne starten, um sie bei
   PV-Überschuss laufen zu lassen.

## Legionellenfunktionen der Wärmepumpe

| # | Funktion  | Auslösung                                   | Ziel dieses Plans           |
|---|-----------|---------------------------------------------|-----------------------------|
| 1 | Periodisch | automatisch, montags 02:00, auf 65 °C       | bleibt vorerst unverändert  |
| 2 | Manuell   | am Bedienteil                                | **remote aktivieren**       |

- Die periodische Funktion wird unter "Erweiterte Einstellungen / Allgemeine
  Einstellungen" (Taste 5 s halten) → "Warmwassereinstellungen / Periodische
  extra WW temp" (JA/NEIN) eingestellt (Handbuch S. 45).
- Sobald der Fernstart zuverlässig funktioniert, kann die periodische Funktion
  abgeschaltet werden. Der Legionellen-Lauf findet dann nur noch tagsüber bei
  PV-Überschuss statt.

Noch offen zur manuellen Funktion:

- Menüpfad am Bedienteil
- Einmaliger Start oder Ein/Aus-Schalter?
- Endet sie von selbst (bei Zieltemperatur oder nach Zeit)?

## Bekannte Fakten

### Busteilnehmer und Rahmenaufbau

- Bedienteil: `41 44 44 52` ("ADDR"), Wärmepumpe: `65 6F DE 02`.
- Schreibrahmen (Beispiel: Stunde setzen):

  ```text
  65 6F DE 02 | d3 5e | 41 44 44 52 | 17  | 57 'W' | 01 02 03 04 | 0B 10   | 01 04 00 | 09   | CRC8
  Ziel = WP     CRCs    Quelle=Panel  Len   Befehl                 Familie   Register   Wert   Maxim
  ```

  Die Wärmepumpe quittiert mit `w`. Rahmen mit 1-Byte-Wert sind 23 Byte lang,
  mit 2-Byte-Wert (LE) 24 Byte.

### Schreibzugriffe im Mitschnitt vom 2026-09-18

Quelle: `captures/comfortzone-flow-20260918-0903.log.gz`. Die gzip-Datei ist am
Ende abgeschnitten.

| Register | Häufigkeit       | Wert                    | Deutung                       |
|----------|------------------|-------------------------|-------------------------------|
| `01D903` | alle ~3 s        | `0000`                  | Herzschlag des Bedienteils    |
| `01DB03` | alle ~3 s        | `0000`                  | Herzschlag des Bedienteils    |
| `01E103` | alle ~3 s        | `013E`                  | Herzschlag, Bedeutung offen   |
| `016805` | alle ~3 s        | 8 Byte, Byte 0 zählt    | Herzschlag, Bedeutung offen   |
| `010400` | einmalig 09:05   | `09`                    | Uhr stellen: Stunde           |
| `010500` | einmalig 09:05   | `05`                    | Uhr stellen: Minute           |
| `010600` | einmalig 09:05   | `00`                    | Uhr stellen: Sekunde          |
| `006106` | einmalig 09:05   | `03`                    | unbekannt                     |

Folgerung: Eine Schreibadresse ist die Basis des Leseregisters plus Byte-Offset.
Die Uhrzeit steht im Leseregister `010400` ab Byte 0.

### Erkenntnisse aus qix67/comfortzone_heatpump

Quelle: <https://github.com/qix67/comfortzone_heatpump>. Die lokale Kopie in
`.upstream-comfortzone/` ist identisch mit `master` (letzter Commit
2024-12-31, "Add a sensor for general alarm").

**Protokollversionen.** Upstream kennt drei Versionen. Keine davon verwendet
unsere Registerfamilie `0B 10`. Registeradressen lassen sich deshalb nicht
direkt übernehmen, nur als Hinweis auf die Struktur.

| Upstream-Version | Familie | Beispiel WW-Soll | Beispiel Raum-Soll |
|------------------|---------|------------------|--------------------|
| 1.6 / 1.8        | `0B 07` | `007D03`         | `00B002`           |
| 2.21             | `0B 0D` | `004103`         | `009002`           |
| unsere           | `0B 10` | Lesen: `004503`  | Lesen: `008902` + 9 |

**Schreiben, als Bedienteil getarnt.** Upstream sendet `W`-Rahmen mit der
Quelladresse des Bedienteils (`controller_addr`) an die WP. Die erwartete
Antwort `w` wird vorab gebaut und Byte für Byte verglichen
(`comfortzone_crafting.cpp`).

**Flags werden über Bitmasken geschaltet.** Das höchste Byte der
Registeradresse kodiert die Operation:

| Präfix | Operation          | Beispiel 1.6 "Extra Warmwasser"        |
|--------|--------------------|----------------------------------------|
| `0x0…` | normal schreiben   | –                                      |
| `0x8…` | Bits setzen (OR)   | `81 19 00`, Wert `0x0001` → an, Antwort `08` |
| `0x4…` | Bits löschen (AND) | `41 19 00`, Wert `0xFFFE` → aus, Antwort `0C` |

Genauso arbeitet der Kaminmodus (`0x0400` / `0xFBFF`). Ein manueller
Legionellen-Start ist sehr wahrscheinlich ebenfalls ein solcher Flag-Befehl.
Im Mitschnitt sind dafür `W`-Rahmen mit Präfix `8x` oder `4x` zu erwarten.

**Busvergabe (`push_settings`).** Gemessen von upstream mit einem
Logikanalysator:

- Die Antwort der WP folgt ~50–60 ms nach einer Anfrage, bei einem Register
  erst nach ~200 ms.
- Zwischen einer Antwort und der nächsten Anfrage des Bedienteils liegen
  2–10 ms.
- Einmal pro Abfragezyklus gibt es eine Pause von ~1,1 s.

Upstream geht so vor:

1. Nach einer WP-Antwort 40 ms warten.
2. Kam in dieser Zeit nichts, DE auf HIGH setzen, senden, `flush`, DE auf LOW.
3. Höchstens 200 ms auf die Quittung warten, sonst neu versuchen, bis zum
   Timeout (Standard 5 s).

**Upstream liefert keinen Legionellen-Befehl.** Upstream unterstützt
Lüfterstufe, Raum-Soll, WW-Soll, LED, Uhrzeit, Extra Warmwasser, Sommerzeit,
Fühler-Offsets und Kaminmodus.

**Namen der Messwerte.** Die Felder der Upstream-Statusstrukturen
(`comfortzone_frame.h`, `comfortzone_status.h`) tragen die Namen aus der
erweiterten Ansicht des Bedienteils. Sie dienen als Namensliste für die
Zuordnung der Fotos.

### Handbuch (`doc/Montage-_und_Bedienungsanleitung_2.0.pdf`)

- **Legionellenschaltung** (S. 45): siehe oben.
- **Extra Warmwasser** (S. 7): wird am Bedienteil mit OK ein- und ausgeschaltet
  und schaltet sich nach 3 h selbst ab.
- **Solar Panel Synchr** (S. 48–49): 0–10-V-Eingang für PV, siehe Phase 7.

## Phase 1 – Gezielter Mitschnitt

Vorbereitung:

- [x] `tools/capture_usb_serial.py` so ändern, dass die gzip-Datei beim Abbruch
      sauber geschlossen und regelmäßig weggeschrieben wird
      (`--flush-seconds`, Standard 10 s).
- [x] Protokollvorlage bereitstellen: `doc/capture-protokoll-vorlage.md`.
- [ ] `raw_frame_logging: true` setzen und die Firmware per OTA installieren.
- [ ] Die Handyuhr genau stellen, damit die Fotozeiten zum Mitschnitt passen.

Ablauf mit laufendem Mitschnitt:

1. Normale und erweiterte Messwert-Ansicht fotografieren, möglichst im
   Leerlauf, beim Heizen und bei Warmwasser. Notieren, wann welche Seite
   geöffnet wird: Das Bedienteil fragt beim Öffnen vermutlich zusätzliche
   Register ab.
2. **Den manuellen Legionellen-Modus starten** und die Zeit sekundengenau
   notieren. Den Lauf durchlaufen lassen und auch das Ende notieren. Einen
   Abbruch nur, wenn er gefahrlos möglich ist, und die Zeit ebenfalls notieren.
3. Extra Warmwasser einschalten und nach etwa 1 min wieder ausschalten. Das
   dient als Vergleich zum Flag-Befehl von upstream (Bits setzen/löschen).
4. Kontrollversuch: das WW-Soll um 0,5 K ändern und zurückstellen. So lässt
   sich das Schreibformat an einem bekannten Register (`004503`) prüfen.

Protokollvorlage:

```text
Uhrzeit (hh:mm:ss) | Aktion / Menüseite             | Foto (Dateiname)
09:12:05           | Erweiterte Ansicht Seite 1      | IMG_6001.JPEG
09:15:30           | Legionellen manuell gestartet   | -
```

## Phase 2 – Auswertung

- [x] Werkzeuge erstellt: `tools/correlate_photos.py` (Fotowerte zuordnen) und
      `tools/analyze_writes.py` (Schreibzugriffe, `--around`,
      `--diff-register --bits`, `--timing`).
- [x] Fotowerte mit `tools/correlate_photos.py` ausgewertet (Mitschnitt und 58 Fotos
      vom 2026-10-30). Alle bekannten Zuordnungen bestätigt, neue gefunden. Ergebnis
      in `doc/capture-analyse-2026-10-30.md`, Menüübersicht in
      `doc/anzeige-menue-uebersicht.md`.
- [x] Legionellen-Befehl gefunden: Start `W 811700 = 01 00`, Stopp `W 411700 = FE FF`,
      Quittung jeweils `2C`, danach liest das Bedienteil `R 011700 02` zurück.
- [x] Statusbit gefunden, aber noch nicht eindeutig: Statuswort `010400`+18 geht von
      `0x0800` auf `0x0B20`, 6,5 s nach dem Start. Welches der drei Bits
      "Legionellen" bedeutet, ist offen (Vergleich mit Extra Warmwasser nötig).
- [x] Heizelement läuft mit: 3500 W, dazu Verdichter 40 Hz. Gesamt ca. 4,9 kW,
      Verzögerung nach dem Start ca. 62 s.
- [ ] Heizungsdurchfluss (`01F901` Byte 18) im Heizbetrieb bestätigen (Foto zeigte 0,0).
- [ ] Extra Warmwasser an/aus aufzeichnen, um das Statusbit zu trennen.
- [ ] Einen vollständigen Legionellenlauf aufzeichnen (Dauer, Leistung, Ende).
- [ ] Offene Punkte aus der Analyse vom 2026-09-18 prüfen: `014003` Byte 10,
      `fan_speed` als High-Byte von `fan_power`.
- [x] Busvergabe aus den Zeitstempeln vermessen (`tools/analyze_writes.py
      --timing`, Mitschnitt 2026-09-18). Ergebnis, nur grob, weil
      Log-Zeitstempel und nicht Leitungszeit:
      - Abfragezyklus ~2,9 s, 45 verschiedene Leseregister.
      - Nächste Anfrage des Bedienteils ~40 ms (Median) nach einer
        WP-Antwort. Upstream nennt 2–10 ms.
      - Keine regelmäßige 1,1-s-Pause wie bei upstream. Nur 2 Lücken
        > 300 ms in 2,3 h, beide vor der Antwort auf `R 050000`.
      - Folgerung: Eine feste Wartezeit von 40 ms reicht nicht. Die genauen
        Lücken müssen auf dem ESP gemessen werden (siehe Phase 4).

## Phase 3 – Neue Sensoren, weiterhin nur lesend

- [ ] Bestätigte Messwerte als Entitäten in `components/comfortzone_ex`
      ergänzen.
- [ ] Binärsensor "Legionellen-Programm aktiv" ergänzen.
- [ ] `PROTOCOL_COVERAGE`, README, Grafana- und HA-Dashboard aktualisieren.

## Phase 4 – Senden auf der Hardware prüfen

Bis hierher wird nichts gesendet. Vor dem ersten Senden zu klären:

- [ ] **Polarität:** Der Empfang läuft derzeit invertiert
      (`rx_pin.inverted: true`). Das deutet auf vertauschte A/B-Leitungen hin.
      Entweder die Adern tauschen und die Invertierung herausnehmen, oder auch
      TX invertieren. Laut upstream zeigt das Bedienteil bei vertauschten Adern
      "Verbindung verloren".
- [ ] **Sendeseite:** den TX-Pin des Waveshare ESP32-S3-RS485-CAN (vermutlich
      GPIO17) prüfen. GPIO21 ist wahrscheinlich die gemeinsame DE/RE-Leitung
      wie bei upstream (LOW = empfangen, HIGH = senden).
- [ ] **Timing auf dem ESP messen:** Die Firmware stempelt Anfang und Ende
      jedes Rahmens mit `micros()` direkt am UART und gibt eine Statistik
      der Lücken aus (Diagnose-Modus, weiterhin ohne Senden). Erst danach
      wird die Ruhezeit vor dem Senden festgelegt.
- [ ] **Sendelogik in ESPHome:** den Ablauf von upstream `push_settings` als
      **nicht blockierenden** Zustandsautomaten in `loop()` umsetzen. Upstream
      blockiert bis zu 5 s, ESPHome verträgt nur wenige Millisekunden.
      - DE erst direkt vor dem Senden auf HIGH setzen, nach dem Senden von
        Hand umschalten.
      - Auch die eigenen gesendeten Bytes als Echo erwarten und herausfiltern.
- [ ] **Erster Sendetest:** nur ein Leserahmen (`R`) für ein Register, das das
      Bedienteil ohnehin abfragt. Erfolgreich ist der Test, wenn die WP
      antwortet und keine zusätzlichen CRC-Fehler oder Störungen am Bedienteil
      auftreten.

## Phase 5 – Schreiben mit Schutzmechanismen

- [ ] Neue Option `allow_write`, standardmäßig `false`.
- [ ] Keine beliebigen Register: nur eine feste Liste der in Phase 1
      beobachteten Rahmen. Die erwartete `w`-Quittung wird wie bei upstream
      vorab gebaut und exakt verglichen.
- [ ] HA-Taste "Legionellen-Programm starten". Falls der manuelle Modus ein
      Schalter ist, auch "Legionellen-Programm stoppen".
- [ ] Senden nur bei RS485 online. Erfolg gilt erst, wenn die Quittung passt
      und das Statusbit gesetzt ist. Höchstens 2 Wiederholungen.
- [ ] Sperrzeit, z. B. höchstens 1 Legionellen-Start pro 24 h.
- [ ] Schreibvorgänge loggen und als Diagnose-Zähler veröffentlichen.
- [ ] Beobachten, ob das Bedienteil den ferngestarteten Zustand anzeigt oder
      ihn mit seinen Herzschlag-Schreibzugriffen überschreibt.
- [ ] Die README anpassen: Das Projekt ist dann nicht mehr rein empfangend.

## Phase 6 – HA-Automation für PV-Überschuss

- [ ] Auslösen, wenn alle Bedingungen erfüllt sind:
      - Überschuss > X W seit 10 min (X aus Phase 2)
      - WW-Temperatur < 60 °C
      - letzter Legionellen-Lauf ≥ N Tage her
      - Uhrzeit zwischen 10 und 15 Uhr
- [ ] Nach einigen erfolgreichen Wochen die periodische Funktion
      ("Periodische extra WW temp") an der WP abschalten. Alternativ in HA eine
      Rückfallregel einbauen: Gab es N Tage keinen PV-Start, wird trotzdem
      gestartet.

## Phase 7 – 0–10-V-PV-Eingang (zurückgestellt)

Wird vorerst nicht umgesetzt, eventuell später.

- Die WP bietet "Solar Panel Synchr" (Nein / WW / WW+HZG) mit einem
  0–10-V-Eingang, wobei 1 V = 1000 W (Handbuch S. 48–49).
- Mögliche Umsetzung: 0–10-V-DAC (z. B. GP8403) am ESP32, aus HA mit
  "Überschuss in W / 1000" angesteuert.
- Diese Variante braucht kein Senden auf dem Bus, ersetzt aber nicht den
  gezielten Legionellen-Start.

## Risiken

- Kollisionen auf dem Bus können die Kommunikation zwischen Bedienteil und WP
  stören. Gegenmaßnahmen: nur in Lücken senden, Quittung prüfen, wenige
  Wiederholungen.
- Die Registerfamilie `0B 10` ist neuer als alles, was upstream kennt. Befehle
  von upstream werden deshalb nie ungeprüft übernommen, nur im Mitschnitt
  beobachtete Rahmen.
- Das Bedienteil kennt den ferngeschalteten Zustand eventuell nicht und zeigt
  ihn nicht an.
- 65 °C mit Heizstab bedeutet hohe Leistung. Deshalb die Sperrzeit und die
  feste Befehlsliste.
