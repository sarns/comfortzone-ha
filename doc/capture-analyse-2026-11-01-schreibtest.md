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

Die Lüfter-Rahmen liefen im Fenster nach `R 049C3E`, die Sollwerte in den Fenstern von 0.6.0. Die Schalter für WW Extra
und Legionellenprävention sind gebaut, aber noch nicht auf dem Bus getestet.

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

CRC-Fehlerzähler 0 in allen Läufen. Im Mitschnitt ab 14:16 fehlten zwei Antworten: um 14:16:34, vor dem ersten
Senden, und um 14:19:08, 73 s nach dem letzten. Beide stehen also nicht in zeitlicher Nähe zu einem Schreibrahmen. Die
Referenz ohne eigenes Senden zeigt denselben Effekt. Die Ursache ist nicht geklärt, möglich sind verlorene Bytes im
Empfang des ESP.

## Offen

- Bedienteil während eines Schreibvorgangs beobachten: Anzeige und mögliche Fehlermeldung.
- Schalter auf dem Bus testen. Beide starten das Heizelement.
- Voller Lauf von WW Extra vom Hauptbildschirm: Abschalten bei 55 °C, Halten, Dauer.
