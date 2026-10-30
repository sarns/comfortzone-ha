# Testergebnisse 2026-10-30, 10:40–11:25

Grundlage: 42 Fotos (IMG_5843–IMG_5885, Abschrift in `fotos-2026-10-30/transkription-tests.json`, Zahlenwerte in
`fotowerte-tests.csv`) und der Mitschnitt `comfortzone-heating-20261030-0851.log.gz` (Stand 11:24).
Die Abschrift stammt von Sonnet-Agents und wurde nur stichprobenartig geprüft.

## Bus-Aktionen

| Zeit | Aktion | Rahmen (Nutzdaten ab Byte 18) | Ack |
|---|---|---|---|
| 10:40:50 | WW Extra = Ja | `W 81 17 00 01 00` (SET Bit 0) | `08` |
| 10:43:00 | WW Extra = Nein | `W 41 17 00 FE FF` (CLEAR Bit 0) | `0C` |
| 10:43:49 | Ventilator Schnell | `W 00 DC 03 03` | `03` |
| 10:44:16 | Ventilator Langsam | `W 00 DC 03 01` | `01` |
| 10:44:35 | Ventilator Normal | `W 00 DC 03 02` | `02` |
| 10:45:57 | WW Einstellungen 45,0 °C | `W 00 45 03 C2 01` | `01` |
| 10:47:29 / 10:49:21 / 10:53:31 | Heizungs-Referenztemp. 23 / 24 / 22 °C | `W 00 92 02 E6 00` / `F0 00` / `DC 00` | `00` |
| 10:56:50 | Sofor. Legionellenpräv. Anfangen | `W 81 17 00 01 00` | `08` |

## Ergebnisse

1. **WW Extra und sofortige Legionellenprävention sind auf dem Bus nicht zu unterscheiden.** Beide senden denselben
   Rahmen `81 17 00 01 00`. Danach ändern sich dieselben Felder: Statuswort `010400`+18 von `0x0800` auf `0x0B20`,
   Heizelement nach ca. 61 s, und das aktive WW-Soll `01F901`+97 springt von 48,0 auf 65,0 °C (`E0 01` → `8A 02`).
   Beide Menüpunkte schalten vermutlich dasselbe Flag (Bit 0 von `0117`). Das Beenden ist ebenfalls gleich
   (`41 17 00 FE FF`): Heizelement aus nach ca. 2 s, Status zurück auf `0x0800`.
   Offen: ob die Zeile "WW Extra" während eines Legionellenlaufs ebenfalls "Ja" zeigt, und wann ein Lauf von selbst endet.
2. **Ventilator:** Die Stufe steht in `004503`+151 (1 = Langsam, 2 = Normal, 3 = Schnell), Schreibadresse `00DC03`.
   Die Ventilatorleistung (`01D102`+2) ist 45,5 % / 65,0 % / 84,5 %, also Normalwert × 0,7 / 1,0 / 1,3.
   Das bisher als `fan_speed` genutzte High-Byte von `fan_power` liefert hier zufällig 1/2/3, ist aber nicht die Einstellung.
3. **Heizungsdurchfluss ist `01D102`+10**, dasselbe Feld wie der Warmwasserdurchfluss (15 von 15 Fotos). Die bisherige
   Zuordnung `01F901`+18 ist falsch: das Feld springt zwischen 0 und 52, unabhängig vom Display.
   Heizung und Warmwasser zeigen denselben Messwert, nur die Betriebsart unterscheidet sie. Ein Merkmal dafür fehlt noch.
4. **Neu bestätigt:** Kondensatortemp. `01D102`+15 (7 Fotos), Kondensatordruck +17, Verdampferdruck +19,
   Druckverhältnis +21 (je 3 Fotos), Berechnete Vorlauftemp. `01F901`+0 (15 Fotos).
5. **Weiter mehrdeutig:** "Erforderliche Leistung" (`01F901`+22 und +30 liefern in allen 15 Fotos denselben Wert),
   Ausgangsstrom (`014003`+85 u8 × 0,01 passt mit 2,55 zu 2,5 Arms, aber nur zwei Datenpunkte, davon einer 0),
   Leistungsteiltemp. (23,4 / 24,0 °C ohne Treffer), Position Ex-Ventil und Überhitzung (je 1 Foto).
6. **Heizlauf:** Sollwert 24 °C um 10:49:21, Verdichter ab 10:51:44 mit 15 Hz, Durchfluss 0,4 → 8,3 l/min im selben Moment.
   Verdichter aus 1 s nach dem Zurücksetzen auf 22 °C (10:53:32).
7. **Legionellenlauf ab 10:56:50:** Heizelement 3500 W ab 10:57:52, Verdichter erst ab 11:06:51 (40 Hz),
   Heizelement 3000 W ab 11:16:58. Warmwassertemp. fällt zuerst auf 45,4 °C und steigt ab 11:02 auf 50,8 °C (11:24).
   Das Ende des Laufs ist noch nicht aufgezeichnet.

## Nachtrag: vollständiger Legionellenlauf (Fotos IMG_5886–IMG_5908, Mitschnitt bis 12:44)

Abschrift: `fotos-2026-10-30/transkription-tests2.json`, Zahlenwerte: `fotowerte-tests2.csv`.

| Zeit | Phase | WW-Temp. | Leistung |
|---|---|---|---|
| 10:56:50 | Start (`W 81 17 00 01 00`), Soll 48 → 65 °C | 45,7 °C | – |
| 10:57:52 | Heizelement ein | 45,6 °C | 3500 W |
| 11:06:51 | Verdichter ein (40 Hz Sollfrequenz) | 45,9 °C | ca. 1,1–1,6 kW Aufnahme + Heizelement |
| 11:16:58 | Heizelement reduziert | 48,7 °C | 3000 W |
| 11:54:34 | Verdichter aus (Status `0x0B20` → `0x0320`) | 58,2 °C | – |
| 11:55:35 | Heizelement allein | 58,3 °C | 5000 W |
| 12:31:03 | Heizelement aus, "Warmwasserproduktion Nein" | 65,0 °C | 0 W |

Dauer bis 65 °C: 94 Minuten. Der Lauf endete **ohne Schreibrahmen vom Panel**: Die Wärmepumpe hört von selbst auf,
wenn das Soll erreicht ist. Eine Haltezeit von 60 min bei 60/65 °C ist bis 12:44 nicht zu sehen.

Ergebnisse:

1. **WW Extra stand während des Legionellenlaufs auf "Ja"** (IMG_5886, 11:32:48). Beide Menüpunkte schalten also
   dasselbe Flag. Die Einstellungen "WW Extra Einstellungen 55,0 °C" und "WW Extra Zeit 180 min" wirken nicht wie
   vermutet: Das Soll war in beiden Fällen 65,0 °C.
2. **Zeitzähler `00C602`+125/+126:** Beim Start springt er von `00 FF` auf `14 05`. Byte 125 zählt alle 10 Minuten
   (zur vollen 10-Minuten-Uhrzeit) um eins herunter, Byte 126 ist die Zehnerstelle der Uhrminute. 20 × 10 min passt
   ungefähr zu "WW Extra Zeit 180 min". Prognose: Byte 125 erreicht 0 gegen 14:10. Dann sollten Statusbit `0x0020` und
   das Soll von 65 °C zurückgehen. Bis dahin heizt die Anlage nach, wenn das Warmwasser unter 65 °C minus Hysterese fällt.
3. **Kompressorfrequenz:** Das Display zeigt 34,4 Hz und der Inverter 36,1 Hz, während `01D102`+33 auf 40,0 stand.
   Die tatsächliche Frequenz ist `01D102`+45 (identisch +47/+49; 5 von 5 Fotos). `+33` ist die Sollfrequenz.
   **Die Firmware publiziert derzeit die Sollfrequenz als `compressor_frequency`.**
4. **Bestätigt (jetzt ≥ 2 Fotos):** Position Ex-Ventil `014003`+88, Soll-Überhitzung +82, Überhitzung +86,
   Kondensatordruck `01D102`+17 (4), Verdampferdruck +19 (4), Druckverhältnis +21 (4), Kondensatortemp. +15 (9).
5. **Weiter offen:** Ausgangsstrom (2,5 / 7,3 / 7,6 Arms) und Leistungsteiltemp. (24–45 °C) haben keinen Treffer in
   den abgefragten Registern. "Erforderliche Leistung": `01F901`+22 und +30 sind in 21 Fotos identisch.
6. **Ende des Boost-Zustands (Mitschnitt bis 15:31):** Von 13:26:39 bis 13:40:39 heizt das Heizelement allein mit
   5 kW nach. Auslöser: das Warmwasser fiel unter 63,5 °C (65 °C − Hysterese 1,5 K). Um 13:50:05 endet der Zustand
   **ohne Schreibrahmen**: Status `0x0724` → `0x0004` (Bit `0x0020` weg), aktives Soll `01F901`+97 65,0 → 45,0 °C,
   Zähler `00C602`+125 → `00 FF` (13:50:34). Dauer ab Start 10:56:50: 173 min. Das passt zu "WW Extra Zeit 180 min",
   gerechnet in 10-Minuten-Takten der Uhr. Der Zähler stand beim Ende auf 3, nicht auf 0. Die Restzeit lässt sich
   daraus nur ungefähr ableiten.
   Ablauf also: aufheizen auf 65 °C, dann bis zum Ablauf der 180 min 65 °C halten (mit 1,5 K Hysterese).
7. **Durchfluss:** Heizungsseite 0,0 l/min im Warmwasserbetrieb (IMG_5890/5892), Warmwasserseite 0,0 im Heizbetrieb.
   Es gibt einen Durchflussmesser (`01D102`+10). Die Seite der inaktiven Betriebsart zeigt 0.
