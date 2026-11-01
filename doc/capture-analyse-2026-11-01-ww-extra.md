# Test WW Extra vom Hauptbildschirm, 2026-11-01

Grundlage: 5 Fotos (IMG_5916–IMG_5920, Zeiten aus den EXIF-Daten) und der Mitschnitt
`comfortzone-wwextra-20261101-1321.log.gz`. Vergleich: Mitschnitt `comfortzone-heating-20261030-0851.log.gz`.

## Ablauf

| Zeit | Ereignis | Beleg |
|---|---|---|
| 13:25:52 | Hauptbildschirm, Symbol "Extra Warmwasser" nicht aktiv | IMG_5916 |
| 13:25:55 | Start: `W 81 1D 00 40 00`, Ack `00` | Mitschnitt |
| 13:25:56 | `010400`+18 `04`→`24`, +19 `08`→`0B`, +25 `04`→`C4`, +28 `00`→`08` | Mitschnitt |
| 13:25:56 | Aktives Soll `01F901`+97 45,0 → 55,0 °C | Mitschnitt |
| 13:25:57 | Symbol "Extra Warmwasser" aktiv | IMG_5917 |
| 13:26:23 | Warmwasserproduktion Ja, Soll 55,0 °C, Ist 44,7 °C, Durchfluss 11,7 l/min | IMG_5918 |
| 13:26:33 | Zähler `00C602`+125 `00 FF` → `14 02` | Mitschnitt |
| 13:27:24 | Kompressorfrequenz 40,0 Hz, Zusatzleistung 3500 W, Gesamtleistung 6437 W | IMG_5920 |
| 13:27:54 | Stopp: `W 41 1D 00 BF FF`, Ack `00` | Mitschnitt |
| 13:27:56 | +18 `24`→`04`, +19 `0B`→`08`, +25 `C4`→`04`, Soll 55,0 → 45,0 °C | Mitschnitt |
| 13:28:36 | Zähler `00C602`+125 → `00 FF` | Mitschnitt |

Der Warmwasserbetrieb (`010400`+28 = `08`) blieb nach dem Stopp bis mindestens 13:33:35 aktiv (Ende des ausgewerteten
Mitschnitts). Das Warmwasser lag um 13:26:23 bei 44,7 °C, also unter dem Soll von 45,0 °C.

## Vergleich mit der Legionellenprävention (2026-10-30, 10:56:50)

| | WW Extra (Hauptbildschirm) | Sofort-Legionellenprävention |
|---|---|---|
| Start | `W 81 1D 00 40 00` | `W 81 17 00 01 00` |
| Stopp | `W 41 1D 00 BF FF` | `W 41 17 00 FE FF` |
| Ack | `00` | `08` / `0C` / `2C` |
| Aktives Soll | 55,0 °C | 65,0 °C |
| `010400`+25 | `C4` | `04` |
| `010400`+18 Bit `0x20` | gesetzt | gesetzt |
| `010400`+19 | `0B` | `0B` |
| `00C602`+125 beim Start | `14` | `14` |

## Folgerungen

1. Es sind zwei getrennte Funktionen. Die Aussage vom 30.10., WW Extra und Legionellenprävention seien dieselbe
   Funktion, stimmt nur für die Menüzeile "WW Extra".
2. Die Einstellung "WW Extra Einstellungen" (55 °C) wirkt beim Start vom Hauptbildschirm.
3. `010400`+25 Bit `0x40` zeigt WW Extra vom Hauptbildschirm an. Bit `0x80` setzt die Steuerung zusätzlich und nimmt
   es beim Stopp wieder weg, obwohl der Rahmen nur `0x40` löscht.
4. `010400`+18 Bit `0x04` war am 01.11. schon vor dem Start gesetzt und am 30.10. um 10:40 nicht. Bedeutung unbekannt.

## Offen

- Verhalten eines vollen Laufs: Abschalten bei 55 °C, Halten, Dauer.
- Was passiert, wenn beide Funktionen gleichzeitig aktiv sind.

Geklärt am 2026-11-01: `41 17 00` beendet einen Lauf von WW Extra nicht und `41 1D 00` keinen Lauf der
Legionellenprävention, beobachtet je 25 s (`capture-analyse-2026-11-01-schreibtest.md`).
