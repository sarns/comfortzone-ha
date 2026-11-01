# Variablenübersicht: neue Sensoren und geplante Schreibwerte

Stand 2026-10-30. Grundlage: `capture-analyse-2026-10-30.md`, `capture-analyse-2026-10-30-tests.md` und die Fotos
in `fotos-2026-10-30/`. Offsets beziehen sich auf den Nutzdatenteil des `r`-Antwortrahmens (ab Byte 21),
Werte sind little-endian. "Fotos" = Anzahl Displayfotos mit verschiedenen Werten, die exakt passen.

## Korrekturen an bestehenden Sensoren

| Sensor | Bisher | Richtig | Beleg |
|---|---|---|---|
| Compressor Frequency | `01D102`+33 | `01D102`+45 u16 /10 (Istfrequenz) | 5 Fotos, u. a. 34,4 Hz bei +33 = 40,0 |
| Heating Flow | `01F901`+18 (meist 0, Rauschen) | `01D102`+10 u16 /10, wenn Heizbetrieb | 21 Fotos |
| Hot Water Flow | `01D102`+10 immer | `01D102`+10 u16 /10, wenn Warmwasserbetrieb | 8 Fotos |
| Calculated Flow Temperature | `002804`+70 (im ganzen Mitschnitt konstant 15,0, vermutlich "HZG Minimum 15,0 °C") | `01F901`+0 s16 /10 | 21 Fotos, 19,8–26,4 °C |
| Fan Speed | High-Byte von `01D102`+2 | `004503`+151 u8: 1 Langsam, 2 Normal, 3 Schnell | 3 Stufen, Schreibtest |

Betriebsart für die Durchfluss-Aufteilung: `010400`+28, Bit `0x08` = Warmwasserbetrieb, Bit `0x04` = Heizbetrieb
(im Leerlauf `0x00` oder `0x04`). Gefunden durch Vergleich der Warmwasser-, Heiz- und Leerlaufzeiträume;
noch nicht mit Fotos beider Seiten im selben Moment bestätigt.

## Neue Nur-Lese-Sensoren

| Name (Vorschlag) | Display | Quelle | Typ / Skala | Einheit | Fotos | Status |
|---|---|---|---|---|---|---|
| Compressor Target Frequency | – | `01D102`+33 | u16 /10 | Hz | – | bekannt (bisher falsch benannt) |
| Condenser Temperature | Kondensatortemp. | `01D102`+15 | s16 /10 | °C | 9 | bestätigt |
| High Pressure | Kondensatordruck | `01D102`+17 | u16 /10 | bar | 4 | bestätigt |
| Low Pressure | Verdampferdruck | `01D102`+19 | u16 /10 | bar | 4 | bestätigt |
| Pressure Ratio | Druckverhältnis | `01D102`+21 | u16 /10 | – | 4 | bestätigt, Diagnose |
| Expansion Valve Position | Position Ex Ventil | `014003`+88 | s16 /10 | % | 2 | bestätigt |
| Superheat | Temperaturdiff. (Exp.-Ventil) | `014003`+86 | s16 /10 | K | 2 | bestätigt |
| Target Superheat | Soll Temperaturdiff. (Exp.-Ventil) | `014003`+82 | s16 /10 | K | 2 | bestätigt, Diagnose |
| Required Heating Power | Erforderliche Leistung | `01F901`+22 | s16 | W | 21 | +22 und +30 bisher identisch |
| Active Hot Water Target | Soll (Seite Warmwasser) | `01F901`+97 | s16 /10 | °C | 13 | bestätigt, eindeutig (55 bei WW Extra vom Hauptbildschirm, 65 bei Legionellen) |
| Hot Water Hysteresis | Eingestell. Hysterese | `004503`+2 | s16 /10 | K | konstant | Diagnose |
| Fan Speed Setting | Ventilator Einstellungen | `004503`+151 | u8 enum | – | 3 | bestätigt |
| Operating Mode | Warmwasserproduktion | `010400`+28 | Bits 0x08/0x04 | – | – | Kandidat |
| Hot Water Boost Active | WW Extra oder Sofor. Legionellenpräv. | `010400`+18 Bit `0x0020` | binary | – | – | bestätigt (Start 10:56:51, Ende 13:50:05) |
| Hot Water Boost Remaining | – | `00C602`+125 | u8, 10-min-Takte | min | – | ungefähr: Start 20, Ende bei 3, `0xFF` = aus |

Verworfen bzw. offen: Ausgangsstrom und Leistungsteiltemp. (kein Treffer in den abgefragten Registern),
WW-Stufen Normal/Hoch (`004503`+4…+56, nur Einstellwerte, geringer Nutzen), Dig. Eingänge, Fehlerstatus.

## Geplante Schreibwerte (aus Home Assistant)

Alle Rahmen wurden vom Panel gesendet und von der Wärmepumpe quittiert. Die Firmware sendet sie nur aus einer festen
Liste. Freie Registeradressen gibt es nicht.

| HA-Entität | Typ | Schreibrahmen (Byte 18 ff.) | Wert | Rücklesen | Beobachtet |
|---|---|---|---|---|---|
| Fan Speed | select (Langsam/Normal/Schnell) | `W 00 DC 03 <v>` | u8: 1 / 2 / 3 | `004503`+151 | 10:43:49, 10:44:16, 10:44:35 |
| Hot Water Target | number | `W 00 45 03 <lo> <hi>` | s16 /10, z. B. 45,0 °C = `C2 01` | `004503`+0 | 10:45:57 |
| Room Setpoint (HZG Referenztemp.) | number | `W 00 92 02 <lo> <hi>` | s16 /10, z. B. 22,0 °C = `DC 00` | `008902`+9 | 09:05:36, 10:47:29, 10:49:21, 10:53:31 |
| Hot Water Extra (55 °C) | switch | an: `W 81 1D 00 40 00`, aus: `W 41 1D 00 BF FF` | Bit `0x40` setzen/löschen | `010400`+25 Bit `0x40`, `01F901`+97 | 2026-11-01 13:25:55, 13:27:54 |
| Immediate Legionella (65 °C) | switch | an: `W 81 17 00 01 00`, aus: `W 41 17 00 FE FF` | Bit `0x01` setzen/löschen | `010400`+18 Bit `0x20` ohne +25 Bit `0x40`, `01F901`+97 | 09:07, 09:09, 10:40, 10:43, 10:56 |

**WW Extra (Hauptbildschirm) und Sofort-Legionellenprävention sind zwei Funktionen mit zwei Rahmen** (Test 2026-11-01,
`capture-analyse-2026-11-01-ww-extra.md`). Die Zeile "WW Extra" im Einstellungsmenü sendet dagegen denselben Rahmen
wie die Legionellenprävention (Test 2026-10-30).

| | WW Extra (Hauptbildschirm) | Sofort-Legionellenprävention |
|---|---|---|
| Start | `W 81 1D 00 40 00` (Bit `0x40` setzen) | `W 81 17 00 01 00` (Bit `0x01` setzen) |
| Stopp | `W 41 1D 00 BF FF` | `W 41 17 00 FE FF` |
| Aktives Soll `01F901`+97 | 55,0 °C ("WW Extra Einstellungen") | 65,0 °C |
| `010400`+25 | `0xC4` | `0x04` (unverändert) |
| `010400`+18 Bit `0x20` / +19 | gesetzt / `0x0B` | gesetzt / `0x0B` |

Unterscheiden lassen sich beide nur über `010400`+25 Bit `0x40`. Bit `0x20` in +18 und `0x0B` in +19 gelten für beide.

Legionellen-Lauf: Soll 65 °C, Heizelement nach ca. 1 min, Verdichter mit 40 Hz Sollfrequenz bis ca. 58 °C, danach
Heizelement 5 kW bis 65 °C. Am 2026-10-30 dauerte der Lauf von 45,7 auf 65 °C 94 Minuten. Die Wärmepumpe beendet
das Aufheizen selbst und hält danach 65 °C (Nachheizen unter 63,5 °C, nur Heizelement 5 kW) bis zum Ablauf von
"WW Extra Zeit" (180 min, gemessen 173 min). Dann fällt der Zustand ohne Schreibrahmen zurück. Wer nur einmal auf
65 °C heizen will, schaltet nach Erreichen von 65 °C wieder aus, sonst kostet das Halten zusätzlich Strom
(am 2026-10-30 ein Nachheizen von 14 min mit 5 kW).

WW Extra vom Hauptbildschirm lief bisher nur 2 Minuten (13:25:55–13:27:54). Das Heizelement lief dabei mit 3,5 kW
(IMG_5920). Ob es bei 55 °C abschaltet, 55 °C bis zum Ablauf der Zeit hält und wie lange es läuft, ist nicht beobachtet.

### Vorgeschlagene Grenzen

| Wert | Bereich in HA | Schritt | Begründung |
|---|---|---|---|
| Hot Water Target | 40,0–55,0 °C | 0,5 | Aktuell 45–48 °C; höher nur über WW Extra oder Legionellenprävention |
| Room Setpoint | 18,0–25,0 °C | 0,5 | Aktuell 21,5–24 °C getestet |
| Fan Speed | 1–3 | – | Nur die drei beobachteten Stufen |

### Sicherheitsregeln für die Firmware

- `allow_write: false` als Standard. Ohne diese Option sendet die Firmware nichts.
- Sendet nur direkt nach einer Anfrage des Bedienteils an `004503`, `008902`, `008D04`, `03BD0D`, `030B0D` oder
  `014003`. Die Wärmepumpe antwortet darauf frühestens nach rund 45 ms, der Schreibrahmen dauert 12,5 ms.
- Nach jedem Schreiben `w`-Quittung abwarten (ca. 220 ms, Zeitlimit 1 s) und den Wert über das normale Polling prüfen.
  Bei fehlender Quittung höchstens zweimal wiederholen, dann Fehler melden. Anforderungen ohne Fenster verfallen nach 30 s.
- Mindestabstand zwischen zwei Schreibvorgängen 1 s. Die WW-Schalter lassen sich erst 60 s nach dem Ausschalten wieder
  einschalten und nicht, solange das andere Programm läuft. Ausschalten geht immer.
- Ein Neustart des ESP sendet nichts.
- Der Panel-Heartbeat (`01D903`, `01DB03`, `01E103`, `016805`) wird nie nachgebildet.
- Die periodische Legionellenprävention (Montag 02:00) bleibt unverändert.

## Offene Punkte vor der Umsetzung

1. Betriebsart-Bit `010400`+28 mit je einem Foto beider Durchfluss-Seiten bestätigen.
2. WW-Schalter auf dem Bus testen. Lüfter und beide Sollwerte sind getestet (`capture-analyse-2026-11-01-schreibtest.md`).
