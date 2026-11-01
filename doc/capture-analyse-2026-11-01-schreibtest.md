# Schreibtest auf dem Bus, 2026-11-01

Grundlage: Mitschnitte `comfortzone-txtest-20261101-1403.log.gz` und `comfortzone-txtest-20261101-1416.log.gz`, Firmware
0.5.0 und 0.6.0. Absender der Rahmen ist die Adresse des Bedienteils.

## Hardware

Laut Schaltplan des ESP32-S3-RS485-CAN: IO17 = TXD, IO18 = RXD, IO21 = `RS485_EN` an DE und RE eines SP3485. Die
Richtung schaltet also die Firmware. Die Busadern sind richtig gepolt, `rx_pin` ist nicht invertiert.

## Ergebnisse

| Zeit | Rahmen | Quittung nach | Rücklesen |
|---|---|---|---|
| 13:58:50 | Lüfter Schnell (3) | ca. 390 ms | `004503`+151 = 3, Lüfterleistung 84,5 % |
| 14:04:00 | Lüfter Langsam (1) | 371 ms | 1, 45,5 % |
| 14:05:03 | Lüfter Normal (2) | 372 ms | 2, 65,0 % |
| 14:16:38 | WW-Soll 47,0 °C | 223 ms | `004503`+0 = 47,0 °C |
| 14:17:11 | WW-Soll 45,0 °C | 237 ms | 45,0 °C |
| 14:17:18 | Raum-Soll 23,0 °C | 229 ms | `008902`+9 = 23,0 °C |
| 14:17:52 | Raum-Soll 22,0 °C | 218 ms | 22,0 °C |
| 15:00:39 | Lüfter Langsam (1), aus HA | 219 ms | 1 |
| 15:00:42 | WW-Soll, aus HA | 211 ms | von der Folgeanforderung überholt |
| 15:00:44 | WW-Soll 44,0 °C, aus HA | 220 ms | 44,0 °C |

Die Lüfter-Rahmen bis 14:05 liefen mit 0.5.0 im Fenster nach `R 049C3E`, alle übrigen in den Fenstern von 0.6.0.

## Schalter

Test um 15:24–15:30 über die native API, jedes Programm rund 2 Minuten. Alle Rahmen wurden beim ersten Versuch
quittiert (178–229 ms). Zeiten ab der Quittung, auf ganze Sekunden nach der Empfangszeit der Zustände:

| Größe | WW Extra | Legionellenprävention |
|---|---|---|
| Schalter und `Hot Water Boost` an | unter 1 s | 2 s |
| Aktives WW-Soll | 55,0 °C nach 32 s | 65,0 °C nach 20 s |
| Heizelement 3500 W | nach 95 s | nach 83 s |
| Schalter aus nach dem Stopp | 2 s | 3 s |
| Heizelement aus und WW-Soll 45,0 °C nach dem Stopp | 37 s | 21 s |

Weitere Ergebnisse:

- Stopp der jeweils anderen Funktion: Das Programm lief in beiden Richtungen weiter, beobachtet 25 s lang (Status,
  aktives Soll und Heizelement unverändert).
- Einschalten der anderen Funktion während eines Laufs lehnt die Firmware ab, der Rahmen geht nicht auf den Bus.
- Einschalten 5 s nach dem Ausschalten lehnt die Firmware ebenfalls ab (Sperrzeit 60 s).

Der Verdichter startete rund 30 s nach dem Einschalten von WW Extra und lief nach dem Test mit rund 22 Hz bei
Warmwasser-Durchfluss weiter, bei 44,3 °C im Speicher. Ob das eine normale Nachladung ist, wurde nicht weiter verfolgt.

## Bedienteil

Die Rahmen um 15:00 kamen aus Home Assistant. Der Nutzer sah die neuen Werte auf dem Display. Um 15:02 stellte das
Bedienteil selbst zurück (`W 00DC03 02`, `W 004503 C201`, ohne eigenen Sendeeintrag der Firmware). Home Assistant zeigt
danach Normal und 45,0 °C, Änderungen am Bedienteil kommen also an.

## Sendefenster

Der Bus ist lückenlos belegt: Zwischen einer Antwort und der nächsten Anfrage liegen im Median 8 ms. Die Wärmepumpe
beginnt ihre Antwort aber erst nach der Anfrage plus einer Bearbeitungszeit. Bei sechs Registern sind das mindestens
rund 45 ms (Logzeit, 1175 s Mitschnitt): `004503`, `008902`, `008D04`, `03BD0D`, `030B0D`, `014003`. Ein Schreibrahmen
dauert 12,5 ms und passt in diese Pause. Alle sechs werden im 2,9-s-Zyklus abgefragt. Das Fenster nach `R 049C3E`
(ca. 217 ms, alle 63 s) wird nicht mehr gebraucht.

Die Wärmepumpe sendet zuerst die laufende Antwort und quittiert dann nach der nächsten Anfrage des Bedienteils:

```text
14:16:38.985 R 014003      Anfrage des Bedienteils
14:16:38.983 W 004503      Unser Rahmen (Logzeile am Ende des Sendens, deshalb vor der Anfrage einsortiert)
14:16:39.136 r 014003      Antwort auf die Anfrage
14:16:39.152 R 012004      Nächste Anfrage
14:16:39.209 w 004503      Quittung, ca. 220 ms nach dem Senden
14:16:39.245 r 012004      Antwort auf die nächste Anfrage
```

Die Quittung passt also nur knapp vor die Antwort auf die nächste Anfrage. Die Bearbeitungszeit bleibt dabei unter den
in der Referenz beobachteten Werten.

## Reaktionszeit

Von der Anforderung bis zum gelesenen neuen Wert vergingen 1,9–3,7 s. Davon entfallen 0,4–0,7 s auf das Warten auf ein
Fenster, rund 0,2 s auf die Quittung und der Rest auf den nächsten Lesezyklus. Die Register werden alle 2,9 s gelesen.

## Busgesundheit

CRC-Fehlerzähler 0 bis zum Testende um 15:30. Im Mitschnitt von 14:16 bis 15:30 fehlten sechs Antworten: um 14:16:34,
vor dem ersten Senden, und um 14:19:08, 14:22:44, 14:38:59, 15:16:20 und 15:22:01, frühestens 76 s nach einem
Schreibrahmen. Keine steht also in zeitlicher Nähe zu einem Schreibrahmen. Die Referenz ohne eigenes Senden zeigt
denselben Effekt (eine in 1175 s). Die Ursache ist nicht geklärt, möglich sind verlorene Bytes im Empfang des ESP.

## Offen

- Wiederholung nach fehlender Quittung und Verfall nach 30 s: Beides trat nicht auf und ist deshalb ungetestet.
- Anzeige des Bedienteils während eines über die Schalter gestarteten Programms.
- Voller Lauf von WW Extra vom Hauptbildschirm: Abschalten bei 55 °C, Halten, Dauer.
