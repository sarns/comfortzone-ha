# Anzeige- und Menüübersicht Comfortzone EX (erweiterte Ansicht)

Abgeschrieben aus 58 Fotos vom 2026-10-30 (IMG_5783–IMG_5840, 08:57–09:09, Aufnahmezeit aus EXIF).
Die Rohabschrift mit allen Zeilen steht in `doc/fotos-2026-10-30/transkription.json`, die numerischen
Werte als `doc/fotos-2026-10-30/fotowerte.csv` (Eingabe für `tools/correlate_photos.py`).

Die Schreibweisen entsprechen dem Display (`Umwaelzpumpe`, `Waermepumpe`). Die Spalte "Bus-Quelle" nennt
Register und Byte-Offset im Nutzdatenteil des Antwortrahmens (`r`). Sie wurde per Abgleich mit dem
Mitschnitt vom 2026-10-30 ermittelt. **bekannt** = bereits in `comfortzone_ex.cpp`, **neu** = erst in
diesem Abgleich gefunden. Leere Zellen heißen: noch nicht zugeordnet oder mehrdeutig. Die Abschrift stammt
von Sonnet-Agents und wurde nur stichprobenartig gegen die Fotos geprüft.

## Menübaum

```text
Grundlegende Einstellungen
Heizung Einstellungen
  Vorlauf Einstellungen / Bodentrocknungsprogr. / Sommermodus / Andere Einstellungen
Warmwasser Einstellungen
  WW Stufe (Normal / Hoch / Extra, je 12 Stufen)
  Per. Legionellenpräv. (enthält "Sofor. Legionellenpräv.")
Ventilator (Kaminoption, Aussenluft, Zeitsteuerung)
Waermepumpe Einstellungen
  WP Kompressor / WP Zusatzheizung / WP Abtauung / WP Test / WP Andere
Systemeinstellungen
Messung
  Ventilator, Heizung, Warmwasser, Expansionsventil, Waermepumpe, Fühler, Dig. Eingänge, Inverter
  Version Information
```

Der Baum ist aus den Fotos abgeleitet, nicht vom Display abgelesen.

## Grundlegende einstellungen

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| Heizungsmodus | Fußbodenhzg. |  | 5783 |
| HZG Betriebsart | Außen & Innen |  | 5783 |
| HZG Heizkurve | 4.0 |  | 5783 |
| HZG Umwaelzpumpe | 76.0% |  | 5783 |
| Vent. normale leistung | 65.0% |  | 5783 |
| Zusatz Leistungsgrenze | 5000 W |  | 5783 |
| Ventil. Einstel. korr. | -30.0% |  | 5784 |
| Zusatzheizung Funktion | Normal |  | 5784 |
| ▶ Heizung Einstellungen |  |  | 5784 |
| ▶ Warmwasser Einstellungen |  |  | 5784 |

## Heizung Einstellungen

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| Urlaubszeit | Nein |  | 5785 |
| Heizungsmodus | Fußbodenhzg. |  | 5785 |
| HZG Betriebsart | Außen & Innen |  | 5785 |
| HZG Heizkurve | 4.0 |  | 5785 |
| HZG Referenztemp. | 21.5°C (später: 22.0°C) | `008902`+9 s16 /10 (bekannt) | 5785 |
| HZG Raumfaktor | 2.0 |  | 5785 |
| E-Heizung Erlaubt | (19.5) -2.0°C |  | 5786 |
| HZG 2 Heizkreise | Nein |  | 5786 |
| ▶ HZG Vorlauf Einstellungen |  |  | 5786 |
| ▶ HZG Bodentrocknungsprogr. |  |  | 5786 |
| ▶ HZG Sommermodus |  |  | 5786 |
| ▶ HZG Andere Einstellungen |  |  | 5786 |
| Sofor. Legionellenpräv. | Aufhören (später: Anfangen) |  | 5834 |
| Legionellenprävention | Nein |  | 5834 |
| Legionellenpräv.tag | Mo |  | 5834 |
| Legionellenpräv.Temp | 65.0°C |  | 5834 |
| Legionellatemp. 1 | 60°C |  | 5834 |
| Legionellatemp. 2 | 65°C |  | 5834 |
| Legionellenzeit 1 | 60 min |  | 5834 |
| WW Extra Zeit | 180 min |  | 5838 |
| WW Kond.temp. zu hoch | 3.0 K |  | 5838 |
| WW Überhitzungsalarm | 73.0°C |  | 5838 |

## HZG Vorlauf Einstellungen

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| HZG Just bei A Temp 10 | 0.0°C |  | 5787 |
| HZG Just bei A Temp 5 | 0.0°C |  | 5787 |
| HZG Just bei A Temp 0 | 0.0°C |  | 5787 |
| HZG Just bei A Temp -5 | 0.0°C |  | 5787 |
| HZG Just bei A Temp -10 | 0.0°C |  | 5787 |
| HZG Just bei A Temp -15 | 0.0°C |  | 5787 |
| ▶ HZG Bodentrocknungsprogr. |  |  | 5788 |

## HZG Sommermodus

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| HZG Sommermodus | Nein |  | 5788 |
| ▶ HZG Andere Einstellungen |  |  | 5788 |
| ▶ Warmwasser Einstellungen |  |  | 5788 |
| ▶ Ventilator |  |  | 5788 |
| ▶ Waermepumpe Einstellungen |  |  | 5788 |

## HZG Andere Einstellungen

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| HZG Urlaubsreduzierung | 10.0°C |  | 5789 |
| HZG Minimum | 15.0°C |  | 5789 |
| HZG Max.FB.Heizung | 45.0°C |  | 5789 |
| HZG Max.Radiator | 70.0°C |  | 5789 |
| HZG Ueberhitz. Hyst. | 20.0°C |  | 5789 |
| HZG Ruecklauftemp.Max | 60.0°C |  | 5789 |
| HZG Umwaelzpumpe | 76.0% |  | 5790 |
| HZG Pumpe Stop bei 0W | Nein |  | 5790 |
| HZG Pumpe Min bei 0W | Ja |  | 5790 |
| HZG Nachlaufzeit | Nein |  | 5790 |
| ▶ Warmwasser Einstellungen |  |  | 5790 |

## Warmwasser Einstellungen

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| WW Extra | Nein |  | 5791 |
| WW Einstellungen | 48.0°C | `004503`+0 s16 /10 (bekannt) | 5791 |
| WW Hysterese | 1.5°C | `004503`+2 s16 /10 (neu) | 5791 |
| WW Prioritaet | Niedrig |  | 5791 |
| WW Smart Lernen | Nein |  | 5791 |
| WW Smart Kontroll | Nein |  | 5791 |
| WW Priorität | Niedrig |  | 5792 |
| WW temp. Min. freq. | 50.0°C |  | 5792 |
| WW Min. freq. Zeit | 5.0 min |  | 5792 |
| ▶ WW Stufe |  |  | 5792 |
| WW Max Zeit | 30 min |  | 5792 |

## WW Stufe

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| WW Normal Stufe 1 | -11.0°C | `004503`+4 s16 /10 (neu) | 5793 |
| WW Normal Stufe 2 | -11.5°C | `004503`+6 s16 /10 (neu) | 5793 |
| WW Normal Stufe 3 | -12.0°C | `004503`+8 s16 /10 (neu) | 5793 |
| WW Normal Stufe 4 | -12.5°C | `004503`+10 s16 /10 (neu) | 5793 |
| WW Normal Stufe 5 | -13.0°C | `004503`+12 s16 /10 (neu) | 5793 |
| WW Normal Stufe 6 | -13.5°C | `004503`+14 s16 /10 (neu) | 5793 |
| WW Normal Stufe 7 | -14.0°C | `004503`+16 s16 /10 (neu) | 5794 |
| WW Normal Stufe 8 | -14.5°C | `004503`+18 s16 /10 (neu) | 5794 |
| WW Normal Stufe 9 | -15.0°C | `004503`+20 s16 /10 (neu) | 5794 |
| WW Normal Stufe 10 | -15.5°C | `004503`+22 s16 /10 (neu) | 5794 |
| WW Normal Stufe 11 | -16.0°C | `004503`+24 s16 /10 (neu) | 5795 |
| WW Normal Stufe 12 | -16.5°C | `004503`+26 s16 /10 (neu) | 5795 |
| WW Hoch Stufe 1 | -5.0°C | `004503`+34 s16 /10 (neu) | 5795 |
| WW Hoch Stufe 2 | -5.0°C | `004503`+36 s16 /10 (neu) | 5795 |
| WW Hoch Stufe 3 | -5.5°C | `004503`+38 s16 /10 (neu) | 5795 |
| WW Hoch Stufe 4 | -5.5°C | `004503`+40 s16 /10 (neu) | 5795 |
| WW Hoch Stufe 5 | -6.0°C | `004503`+42 s16 /10 (neu) | 5796 |
| WW Hoch Stufe 6 | -6.0°C | `004503`+44 s16 /10 (neu) | 5796 |
| WW Hoch Stufe 7 | -6.5°C | `004503`+46 s16 /10 (neu) | 5796 |
| WW Hoch Stufe 8 | -6.5°C | `004503`+48 s16 /10 (neu) | 5796 |
| WW Hoch Stufe 9 | -7.0°C | `004503`+50 s16 /10 (neu) | 5796 |
| WW Hoch Stufe 10 | -7.0°C | `004503`+52 s16 /10 (neu) | 5796 |
| WW Hoch Stufe 11 | -7.5°C | `004503`+54 s16 /10 (neu) | 5796 |
| WW Hoch Stufe 12 | -7.5°C | `004503`+56 s16 /10 (neu) | 5797 |
| WW Extra Stufe 1 | 0.0°C |  | 5797 |
| WW Extra Stufe 2 | 0.0°C |  | 5797 |
| WW Extra Stufe 3 | 0.0°C |  | 5797 |
| WW Extra Stufe 4 | 0.0°C |  | 5797 |
| WW Extra Stufe 5 | 0.0°C |  | 5797 |
| WW Extra Stufe 6 | 0.0°C |  | 5797 |
| WW Extra Stufe 7 | 0.0°C |  | 5798 |
| WW Extra Stufe 8 | 0.0°C |  | 5798 |
| WW Extra Stufe 9 | 0.0°C |  | 5798 |
| WW Extra Stufe 10 | 0.0°C |  | 5798 |
| WW Extra Stufe 11 | 0.0°C |  | 5798 |
| WW Extra Stufe 12 | 0.0°C |  | 5798 |
| WW Max Zeit | 30 min |  | 5798 |
| WW Pausenzeit | 20 min |  | 5799 |
| WW Kompr.freq. min | 15.0 Hz |  | 5799 |
| WW Kompr.freq. max | 40.0 Hz |  | 5799 |
| WW Extra Einstellungen | 55.0°C |  | 5799 |
| WW Extra Zeit | 180 min |  | 5800 |
| WW Kond.temp. zu hoch | 3.0 K |  | 5800 |
| WW Überhitzungsalarm | 73.0°C |  | 5800 |
| ▶ Per. Legionellenpräv. |  |  | 5800 |

## Per. Legionellenpräv.

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| Sofor. Legionellenpräv. | Aufhören (später: Anfangen) |  | 5801 |
| Legionellenprävention | Nein |  | 5801 |
| Legionellenpräv.tag | Mo |  | 5801 |
| Legionellenpräv.Temp | 65.0°C |  | 5801 |
| Legionellatemp. 1 | 60°C |  | 5801 |
| Legionellatemp. 2 | 65°C |  | 5801 |
| Legionellenzeit 1 | 60 min |  | 5802 |
| Legionellenalarm | Nein |  | 5802 |
| Protokol.Legionel.präv. | Nein |  | 5802 |
| ▶ Ventilator |  |  | 5802 |
| ▶ Waermepumpe Einstellungen |  |  | 5802 |
| WW Extra Zeit | 180 min |  | 5840 |
| WW Kond.temp. zu hoch | 3.0 K |  | 5840 |
| WW Überhitzungsalarm | 73.0°C |  | 5840 |

## Ventilator

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| Ventilator Einstellungen | Normal |  | 5803 |
| Ventilator Kaminoption | Nein |  | 5803 |
| Ventil. Normale Leistung | 65.0% |  | 5803 |
| Ventilator min. Leistung | -30.0% |  | 5803 |
| Ventilator max. Leistung | 30.0% |  | 5803 |
| Ventil. Einstel. korr. | -30.0% |  | 5803 |
| Ventilator Leistung aus | Nein |  | 5804 |
| ▶ Aussenluft |  |  | 5804 |
| ▶ Kaminoption Einstellen |  |  | 5804 |
| ▶ Ventilator Zeitsteuerung |  |  | 5804 |
| Aussenluft | Nein |  | 5805 |
| Aussenl.Vent.Geschw. | +20% |  | 5805 |
| Aussenl.Temp.Grenze | 5°C |  | 5805 |
| FS Zuluftvent Einstellen | 70.0% |  | 5806 |
| FS Nachlaufzeit | 5.0 min |  | 5806 |
| Kaminoption Zeit Ende | 120 min |  | 5806 |
| Filterwechsel zeit | 79 d |  | 5806 |
| Niedrig an Wochentagen | Nein |  | 5807 |
| Niedrig an Wochenende | Nein |  | 5807 |
| Norm.Drehz. w. Kompr. ein | Ja |  | 5807 |

## Waermepumpe Einstellungen

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| ▶ WP Kompressor |  |  | 5808 |
| Kompr.Freq.Max | 82.0 Hz |  | 5808 |
| Nachtfreq. max | 82.0 Hz |  | 5808 |
| Nacht Start | 22:00 |  | 5808 |
| Nacht Stop | 07:00 |  | 5808 |
| Kompr Freq. Block 1 | 0.0 Hz |  | 5808 |
| Kompr Freq. Block 2 | 0.0 Hz |  | 5809 |
| Kompr Freq. Block 3 | 0.0 Hz |  | 5809 |
| Kompr Freq. Block 4 | 0.0 Hz |  | 5809 |
| Kompr Freq. Block 5 | 0.0 Hz |  | 5809 |
| ▶ WP Zusatzheizung |  |  | 5809 |
| ▶ WP Abtauung |  |  | 5809 |
| Zusatzheizung Funktion | Normal |  | 5810 |
| Zusatz Leistungsgrenze | 5000 W |  | 5810 |
| ▶ WP Test |  |  | 5810 |
| ▶ WP Andere |  |  | 5810 |
| ▶ Systemeinstellungen |  |  | 5810 |
| Abtau. Block. Temp. | 5.0°C |  | 5811 |
| Abt. Verzoegerung | 50.0 min |  | 5811 |

## WP Test

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| WP Test | Nein |  | 5812 |
| Ventilator | 0.0% |  | 5812 |
| Umwälzpumpe | 0.0% |  | 5812 |
| Warmwasser | Nein |  | 5812 |
| EEV | Nein (später: 0.0%) |  | 5812 |
| Kompressor | Nein (später: 0.0 Hz) |  | 5813 |
| Heizelement 1 | Nein |  | 5813 |
| Heizelement 2 | Nein |  | 5813 |
| Heizelement 3 | Nein |  | 5813 |
| Heizelement 4 | Nein |  | 5814 |
| Zuluftventilator | 0.0% |  | 5814 |
| Leistungstest | Nein |  | 5814 |

## WP Andere

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| Umwälzpumpe iPWM im Ein... | Ja |  | 5815 |
| Umwaelzp. Min | 0.0 l/min |  | 5815 |
| ▶ EEV einstellen |  |  | 5815 |
| ▶ Externes Mischventil |  |  | 5815 |
| ▶ Sonnenkollektor |  |  | 5815 |
| ▶ Systemeinstellungen |  |  | 5815 |
| EEV Max pos | 50.0% |  | 5816 |
| Ext. Mischvent. im Einsatz | Nein |  | 5817 |
| Solar-Panel-Synchr | Nein |  | 5818 |
| ▶ Messung |  |  | 5818 |
| ▶ Version Information |  |  | 5818 |

## Messung

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| ▶ Ventilator |  |  | 5819 |
| Ventilatorleistung | 65.0% | `01D102`+2 u16 /10 (bekannt) | 5819 |
| Vent. einstellen | Normal |  | 5819 |
| Zeit Filterwechsel | 79 d | `00F703`+6 u16, Tage (bekannt) | 5819 |
| ▶ Heizung |  |  | 5819 |

## Heizung

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| Erforderliche Leistung | 668 W | `01F901`+22 oder +30 s16 (mehrdeutig) | 5820 |
| Gewuenschte Raumtemp. | 21.5°C | `008902`+9 s16 /10 (bekannt, Schreibadresse `009202`) | 5820 |
| Raumtemperatur | 22.2°C | `010400`+58 s16 /10 (bekannt) | 5820 |
| Berechnete Vorlauftemp. | 24.3°C | `01F901`+0 s16 /10 (neu, eindeutig) | 5820 |
| Vorlauftemperatur | 24.8°C | `010400`+54 s16 /10 (bekannt) | 5820 |
| Heizungsdurchfluss | 0.0 l/min | `01F901`+18 s16 /10 (vorläufig; Foto zeigt nur 0.0) | 5820 |

## Warmwasser

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| Warmwasserproduktion | Ja |  | 5821 |
| Soll Temperaturdiff. | 48.0°C | `004503`+0 s16 /10 (bekannt, WW-Sollwert) | 5821 |
| Warmwassertemp. | 46.1°C | `010400`+100 s16 /10 (bekannt) | 5821 |
| Eingestell. Hysterese | 1.5°C | `004503`+2 s16 /10 (neu) | 5821 |
| Temporäre Hysterese | Nein |  | 5821 |
| Warmwasserdurchfluss | 11.4 l/min | `01D102`+10 s16 /10 (bekannt) | 5821 |

## Expansionsventil

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| Position Ex Ventil | 15.1% | `014003`+88 s16 /10 (neu) | 5822 |
| Soll Temperaturdiff. | 29.7 K | `014003`+82 s16 /10 (neu, Soll-Überhitzung) | 5822 |
| Temperaturdiff. | 17.9 K | `014003`+86 s16 /10 (neu, Überhitzung) | 5822 |

## Waermepumpe

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| ▶ Fühler |  |  | 5822 |
| ▶ Dig. Eingänge |  |  | 5822 |
| ▶ Expansionsventil |  |  | 5823 |
| Kompressorfrequenz | 23.3 Hz | `01D102`+33 u16 /10 (bekannt) | 5823 |
| Kompressorleistung | 1923 W | `014003`+0 u16 (bekannt) | 5823 |
| Zusatzleistung | 0 W | `014003`+2 u32 (bekannt) | 5823 |
| Gesamtleistung | 1923 W | `014003`+6 u32 (bekannt) | 5823 |
| Kompr.aufnahmeleist. | 979 W | `014003`+14 u16 (bekannt) | 5823 |
| Kondensatortemp. | 48.3°C | `01D102`+15 s16 /10 (neu) | 5824 |
| Kondensatordruck | 30.2 bar | `01D102`+17 u16 /10 (neu) | 5824 |
| Verdampferdruck | 9.5 bar | `01D102`+19 u16 /10 (neu) | 5824 |
| Druckverhältnis | 3.1 | `01D102`+21 u16 /10 (neu) | 5824 |
| Kompressorener... | 14141.23 kWh | `052800`+4 u32 /100 (bekannt) | 5824 |
| Zusatzenergie | 122.64 kWh | `052800`+8 u32 /100 (bekannt) | 5824 |
| Warmwasserene... | 4778.99 kWh | `052800`+12 u32 /100 (bekannt) | 5825 |
| Kompressorzeit | 5761:27 | `052800`+16 u32, Minuten (bekannt) | 5825 |
| Gesamtlaufzeit | 17325:46 | `052800`+20 u32, Minuten (bekannt) | 5825 |

## Fühler

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| TE0 Außentemp. | 8.5°C | `010400`+52 s16 /10 (bekannt) | 5826 |
| TE1 Vorlauftemp. | 24.8°C | `010400`+54 s16 /10 (bekannt) | 5826 |
| TE2 Rücklauftemp. | 46.7°C | `010400`+56 s16 /10 (bekannt) | 5826 |
| TE3 Raumtemp. | 22.2°C | `010400`+58 s16 /10 (bekannt) | 5826 |
| TE4 Heissgastemp. | 66.4°C (später: 66.5°C) | `010400`+60 s16 /10 (bekannt) | 5826 |
| TE5 Kondens. Ausg. | 47.4°C | `010400`+62 s16 /10 (bekannt) | 5826 |
| TE6 Verdampfer Eing. | 5.2°C | `010400`+64 s16 /10 (bekannt) | 5827 |
| TE7 Fortlufttemp. | 3.4°C | `010400`+66 s16 /10 (bekannt) | 5827 |
| TE24 Warmwasser | 46.2°C | `010400`+100 s16 /10 (bekannt) | 5827 |
| ▶ Dig. Eingänge |  |  | 5827 |

## Dig. Eingänge

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| IN1 Hochdruck Alarm | 0 0 |  | 5828 |
| IN2 Inverter Alarm | 0 0 |  | 5828 |
| IN3 Heizung ueberhitzt | 1 1 |  | 5828 |
| IN4 Niederdruck Alarm | 1 1 |  | 5828 |
| IN5 EEV Fehler | 0 0 |  | 5828 |
| IN6 Eingabe | 0 |  | 5828 |
| IN7 Eingabe | 0 |  | 5829 |
| IN8 Eingabe | 0 |  | 5829 |
| PI1 Eingabe | 0 |  | 5829 |
| PI2 Eingabe | 0 |  | 5829 |
| HL1 Eingabe | 0 |  | 5829 |
| HL2 Eingabe | 1 |  | 5830 |
| ▶ Inverter |  |  | 5830 |
| ▶ Version Information |  |  | 5830 |

## Inverter

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| Steuerfrequenz | 23.30 Hz |  | 5831 |
| Ein/Aus-Signal | Ja |  | 5831 |
| Ausgangsfrequenz | 23.30 Hz |  | 5831 |
| Ausgangsstrom | 6.3 Arms | `010400`+102 s16 /10 (wahrscheinlich, 1 Foto) | 5831 |
| Leistungsteiltemp. | 36.2°C |  | 5831 |
| Fehlerstatus | 0 |  | 5831 |

## Version Information

| Menüpunkt | Wert | Bus-Quelle | Foto |
|---|---|---|---|
| ▶ Messung |  |  | 5832 |
| UI Software Version | 2.22.0 |  | 5832 |
| UI Hardware Version | H |  | 5832 |
| Steuerung Version | 2.50 |  | 5832 |
| WP Box Version | 3 |  | 5832 |
| Inverter | 4.1 |  | 5832 |
| ▶ Grundlegende einstellungen |  |  | 5833 |
