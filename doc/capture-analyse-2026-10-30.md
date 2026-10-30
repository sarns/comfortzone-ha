# Capture-Analyse 2026-10-30 (Zwischenstand)

Mitschnitt: `comfortzone-heating-20261030-0851.log.gz` auf `rpi-dev` (läuft bis ca. 20:51).
Ausgewertet wurde ein Snapshot bis 09:23:53 (34.219 gültige Rahmen). Fotos: 58 Stück,
siehe `doc/anzeige-menue-uebersicht.md`. Die Zeiten sind Pi-Zeit (NTP) bzw. EXIF-Zeit des
Handys. Sie passen auf die Sekunde zusammen.

Das Raw-Logging war an und der Empfang lief **nicht invertiert** (A/B getauscht). Es
gab seit dem Umklemmen keine neuen CRC-Fehler.

## 1. Bedienaktionen auf dem Bus

| Zeit         | Aktion (Nutzer)                         | Rahmen auf dem Bus                                     |
|--------------|-----------------------------------------|--------------------------------------------------------|
| 09:05:36.295 | Heizungs-Referenztemperatur 21,5 → 22,0 | `W 009202` = `DC 00` (220), Quittung `00`              |
| 09:07:30.945 | Legionellen sofort **Anfangen**         | `W 811700` = `01 00`, Quittung `2C`                    |
| 09:07:53.084 | (laut Fotos keine Eingabe bekannt)      | `W 811700` = `01 00`, identisch                        |
| 09:09:28.696 | (laut Fotos keine Eingabe bekannt)      | `W 811700` = `01 00`, identisch                        |
| 09:09:34.275 | Legionellen sofort **Aufhören**         | `W 411700` = `FE FF`, Quittung `2C`                    |

Die Zeiten weichen von deiner Schätzung ab: Der Start war um 09:07:30 (nicht 09:06),
der Stopp um 09:09:34, also nach 2 min 4 s. Die EXIF-Zeiten der Fotos 5836 (09:07:29,
Dialog "Anfangen") und 5839/5840 (09:09:32/35, Dialog "Aufhören") passen dazu.

### Ablauf eines Schreibzugriffs (beide Fälle gleich)

```text
Bedienteil → WP   W <Register> <Wert, 1–2 Byte>        (Rahmen 23–24 Byte)
WP → Bedienteil   w <Register> <Quittung, 1 Byte>      ca. 50–60 ms später
Bedienteil → WP   R <Register ohne Flag-Präfix> 02     ca. 30 ms später (Rücklesen)
WP → Bedienteil   r <Register> <2 Byte>                ca. 55 ms später
```

Die Quittung ist das **High-Byte** des 16-Bit-Registerworts nach dem Schreiben: Beim
Sollwert (`DC 00`) ist sie `00`, beim Legionellen-Register (`.. 2C`) ist sie `2C`.
Das Bedienteil liest nach jedem Schreiben das Wort zurück.

### Flag-Register `0117` (Bank 00)

Das oberste Bit-Paar der Adresse wählt die Operation, wie bei upstream beschrieben:

| Präfix | Operation       | Beobachtet                  | Wirkung                            |
|--------|-----------------|-----------------------------|------------------------------------|
| `0x80` | Bits setzen     | `81 17 00` + `01 00`        | Bit 0 setzen → Legionellen starten |
| `0x40` | Bits löschen    | `41 17 00` + `FE FF`        | Bit 0 löschen → Legionellen stoppen |
| `0x00` | plain schreiben | `00 92 02` + `DC 00`        | Wert setzen (Raumsoll)             |

Rücklesen von `011700`: `0B 2C` während des Programms, `08 2C` direkt nach dem Stopp.
Bit 0 ist das Anforderungs-Bit, das das Bedienteil schreibt. Bit 1 war schon beim
ersten Rücklesen gesetzt und verschwand mit dem Stopp. Es wird vermutlich von der Steuerung
selbst gesetzt (Programm aktiv). Das ist noch nicht belegt, weil das Register sonst nie
gelesen wird.

Das Raumsoll-Register `0092` Bank 02 liegt im Lesebereich `008902` bei Offset 9 (`0x92 - 0x89`).
Das bestätigt die Regel "Schreibadresse = Basis des Leseregisters + Byte-Offset". Das
Lesefeld sprang bei 09:05:36.851 von `D7` (21,5) auf `DC` (22,0).

## 2. Statusrückmeldung der Legionellenfunktion

Mehrere Lesefelder schalten genau mit dem Programm um. Die Verzögerung gegenüber dem
Schreibbefehl (Start 09:07:30.9, Stopp 09:09:34.3):

| Register  | Offset | Ruhe      | Aktiv     | Start +  | Stopp +  |
|-----------|--------|-----------|-----------|----------|----------|
| `00C602`  | 125/126 | `FF00`    | `0014`    | 1,5 s    | 1,4 s    |
| `010000`  | 22/23  | `0800`    | `0B20`    | 2,4 s    | 2,4 s    |
| `011302`  | 71/72/79 | `01E0 .. 00` | `028A .. 0F` | 3,0 s | 2,9 s    |
| `010400`  | 18/19  | `0800`    | `0B20`    | 6,5 s    | 6,4 s    |

`010400` Offset 18 (u16, LE) ist der naheliegende Kandidat für die Firmware, weil dieses
Register ohnehin schon gelesen wird: **`0x0800` = Ruhe, `0x0B20` = Legionellenprogramm
aktiv**. Es sind drei Bits, die gleichzeitig kippen (`0x0020`, `0x0100`, `0x0200`).
Welches davon "Legionellen" bedeutet und welche allgemein "Warmwasser erhöht" bedeuten,
ist **offen**. Dazu braucht es einen zweiten Versuch (siehe Abschnitt 5).

## 3. Reaktion der Anlage

Aus den Lesewerten (Register `01D102`, `014003`, `010400`):

| Zeit     | Ereignis                                                                 |
|----------|--------------------------------------------------------------------------|
| 09:07:30 | Startbefehl. Anlage lief schon mit Warmwasser: 23,6 Hz, 995 W elektrisch |
| 09:08:32 | **+62 s:** Heizelement an, `014003` Offset 2 (u32) = **3500 W**           |
| 09:08:42 | Verdichter 23,6 → **40,0 Hz** (= "WW Kompr.freq. max")                   |
| 09:09:11 | Verdichter-Aufnahme 995 → 1442 W, Heizelement 3500 W: **ca. 4,9 kW** gesamt |
| 09:09:34 | Stoppbefehl                                                              |
| 09:09:40 | Statuswort wieder `0800`; Heizelement und 40 Hz bis hierhin aktiv        |
| 09:09:52 | Verdichter zurück auf ~24 Hz, Heizelement aus                            |

Folgerungen für die PV-Steuerung:

- Das Programm schaltet **das 3,5-kW-Heizelement zu**, nicht nur den Verdichter.
  Für 65 °C braucht es also rund **5 kW Überschuss**.
- Die Anlage reagiert erst nach etwa einer Minute. Die Warmwassertemperatur stieg in den
  2 min nur von 46,7 auf 46,9 °C. Wie lange der Lauf bis 65 °C dauert und wann die
  Steuerung ihn selbst beendet, ist **nicht gemessen**. Im Menü stehen "Legionellatemp. 1"
  = 60 °C, "Legionellatemp. 2" = 65 °C und "Legionellenzeit 1" = 60 min. Wie diese Parameter
  zusammenspielen, ist eine Annahme.
- Der Stopp wirkt innerhalb von ~10 s. Ein Fernstopp ist mit demselben Mechanismus möglich.

## 4. Abgleich Display ↔ Bus

`tools/correlate_photos.py` mit `doc/fotos-2026-10-30/fotowerte.csv` (165 Werte,
117 Bezeichnungen) gegen den Mitschnitt. **Alle bisher im Code verwendeten Zuordnungen
bestätigen sich** (Temperaturen, Leistungen, Energiezähler, Durchflüsse, Laufzeiten).
Zusätzlich neu bzw. bestätigt:

| Anzeige                          | Register / Offset                   | Sicherheit            |
|----------------------------------|-------------------------------------|-----------------------|
| Kondensatortemp.                 | `01D102`+15 s16 /10                 | eindeutig             |
| Kondensatordruck                 | `01D102`+17 u16 /10                 | eindeutig             |
| Verdampferdruck                  | `01D102`+19 u16 /10                 | eindeutig mit Wissen vom 18.09. |
| Druckverhältnis                  | `01D102`+21 u16 /10                 | eindeutig mit Wissen vom 18.09. |
| Position Expansionsventil        | `014003`+88 s16 /10                 | passt zu 18.09.       |
| Soll-Überhitzung (29,7 K)        | `014003`+82 s16 /10                 | eindeutig             |
| Überhitzung (17,9 K)             | `014003`+86 s16 /10                 | eindeutig             |
| Berechnete Vorlauftemp. (24,3)   | `01F901`+0 s16 /10                  | eindeutig             |
| Ausgangsstrom Inverter (6,3 A)   | `010400`+102 s16 /10                | wahrscheinlich, 1 Foto |
| WW Hysterese                     | `004503`+2 s16 /10                  | passt zur Menüreihenfolge |
| WW Normal Stufe 1–12             | `004503`+4, +6 … +26 (s16 /10)      | lückenlos in Menüreihenfolge |
| WW Hoch Stufe 1–12               | `004503`+34, +36 … +56 (s16 /10)    | lückenlos in Menüreihenfolge |

Nicht zugeordnet oder mehrdeutig: "Erforderliche Leistung" (`01F901`+22 oder +30),
"Leistungsteiltemp." (nur ein unplausibler Treffer), alle übrigen Einstellungswerte
(konstant und nur auf einem Foto, daher viele Zufallstreffer). Digitale Eingänge und
Fehlerstatus sind Bitfelder, die das Werkzeug nicht dekodiert.

**Heizungsdurchfluss:** Das Display zeigt zur Fotozeit 0,0 l/min, `01F901`+18 liefert
ebenfalls 0. Die Zuordnung ist damit weiter **nicht** im Heizbetrieb bestätigt. Dafür
braucht es ein Foto bei laufender Heizung mit Durchfluss > 0.

## 5. Offene Punkte und nächste Schritte

1. **Drei identische SET-Rahmen** (09:07:30, 09:07:53, 09:09:28). Hast du zwischen den
   Fotos 5837 (09:07:34) und 5838 (09:09:23) etwas gedrückt, z. B. um 09:07:53 noch einmal
   "Anfangen"? Wiederholte SETs sind harmlos (Bits setzen ist idempotent), aber wir wollen
   wissen, was das Bedienteil auslöst.
2. **Welches der drei Statusbits heißt "Legionellen"?** Vorschlag: im laufenden Mitschnitt
   einmal **Extra Warmwasser** an und nach ca. 1 min wieder aus, danach das Bit-Muster in
   `010400`+18 vergleichen. Gleiches gilt für den Schreibbefehl von Extra Warmwasser
   (vermutlich ein weiteres Bit in `0117` oder einem Nachbarregister).
3. **Ein vollständiger Legionellenlauf** (bis zur Selbstabschaltung der Steuerung) zeigt,
   wie lange er dauert, wie hoch die Leistung wird und wie das Ende aussieht. Das ist für
   die PV-Automation wichtig.
4. **Heizbetrieb**: ein Foto der Seite "Heizung" bei Durchfluss > 0, um `01F901`+18
   zu bestätigen.
5. Weiterhin gültig aus Phase 4: Timing der Rücklese-Antwort und der Lücken muss auf dem
   ESP gemessen werden. Aus dem Mitschnitt: Quittung ca. 50–60 ms nach `W`, Rücklesen
   ca. 30 ms nach der Quittung.

## 6. Konsequenzen für den Plan

- Der **Legionellen-Befehl ist bekannt**: `W 811700 01 00` (Start) und `W 411700 FE FF`
  (Stopp). Der erste Sendetest in Phase 4 kann ein harmloser **Lesebefehl** auf dasselbe
  Register sein (`R 011700 02`), den das Bedienteil ohnehin sendet.
- Erfolgskontrolle: Quittung `2C` **und** Statuswort `010400`+18 ≠ `0800` innerhalb von
  ~10 s.
- Die Sperrzeit in Phase 5 ist wichtiger geworden, weil der Start ein 3,5-kW-Heizelement
  zuschaltet. Außerdem muss der Stopp erreichbar bleiben (Taste "Legionellen stoppen").
