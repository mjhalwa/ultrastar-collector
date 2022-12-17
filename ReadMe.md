# UltraStar Deluxe Video und Musik Sammler

## Dependencies

- Python 3.11.0
- ursprünglich entwickelt auf Windows 11
- ffmpeg installiert und im System-Pfad
- youtube-dl installiert und im System-Pfad

## Input

Verzeichnis, das je Lied folgende Dateien enthält

- `{Name}.txt` ... Spiel-Dateien von z.B.[http://usdb.animux.de](http://usdb.animux.de)
- `{Name}.url` ... Youtube-Link-Datei zum Video, dass zum Lied passt (Quelle für mp3- und Video-Datei)
- `{Name} - Cover.jpg` ... Voransicht-Bild
- `{Name}.info` ... Optionale Text-Datei, die 1:1 in das Ergebnisverzeichnis übernommen wird für z.B. `BPM`- oder `GAP`-Vorschläge der Kommentare auf [http://usdb.animux.de](http://usdb.animux.de)

Der Benennung der Dateien `{Name} = {Artist} - {Title}` wird direkt für die Ausgabe verwendet. __Alle Dateien mit gleichem Namen werden zusammen verarbeitet__.

## Ausgabe

Je Input-Gruppe `{Name}` ein Verzeichnis `{Name}`  mit folgenden Dateien

- `{Name}.ori` ... 1:1 `{Name}.txt` aus dem Input
- `{Name}.txt` ... angepasste Spiel-Datei mit z.B. ausgefülltem `MP3`-, `Video`- und `Cover`-Zeilen
- `{Name}.url` ... 1:1 aus dem Input
- `{Name} - Cover.jpg` ... 1:1 aus dem Input als `#COVER` in `{Name}.txt`
- `{Name}.mp3` ... extrahierte Musik-Datei aus Youtube-Video als `#MP3` in `{Name}.txt`
- `{Name} {Auflösung}.mp4` ... min. 1, max. 2 Video-Dateien von Youtube. Versucht wird 1x ein Video mit Audiodatei und 1x ein Video mit bester Auflösung (max 720p, sonst ruckelt das Spiel) herunterzuladen (Falls es ein 720p-Video mit Audio gibt, dann nur 1 Datei). Das Video mit der besseren Auflösung dient als `#VIDEO` in `{Name}.txt`, aus dem Video mit Audio-Datei wird diese als `mp3` extrahiert.

## Extra Skripte

- `beat_shifter.py` - erhöht bzw. verringert den Beat (2. Spalte) in jeder Zeile einer Spiel-Datei ab einer manuell eingefügten Leerzeile

  Wenn alle Zeilen ab einer bestimmten Zeile um einen konstanten {{SHIFT}} erhöht werden müssen, dann
  
  1. vor der ersten zu ändernden Zeile eine Leerzeile einfügen und die txt-Datei speichern.
  2. Dann das Skript auf diese Datei anwenden und positiven/negativen Shift eingeben

      ``` ps1
      python beat_shifter.py {{FILE}} {{SHIFT}}
      ```

      - `{{FILE}}` ... Pfad zu einer txt-Datei
      - `{{SHIFT}}` ... Anzahl zu erhöhende Beats (bei Verringerung negativen Wert eingeben)
  
  3. Die Ausgabe auf der Konsole in die txt-Datei auf der Leerzeile kopieren

  __Notiz:__ aktuell bricht das Skript noch mit einem Fehler bei der letzten Zeile `E` ab.

## Test Daten

Test starten

``` ps1
python ultrastar-collector.py ./test
```

- `Die Ärzte - Deine Schuld`: Umlaute in Titel, Dateiname und Text
- `Die Ärzte - Junge`: `-F` enthält eine `DASH video` Datei, die eine bessere Auflösung unter 720p bieten würde
- `Die Ärzte - Männer sind Schweine`: leiser als andere Lieder
- `Die Prinzen - Alles Nur Geklaut`: keine besseren aber `DASH video`s und Text mit fehlenden Spaces zwischen den Wörtern
- `Disney's Aladdin - A Whole New World`: Volle Youtube-URL, `ARTIST` und `TITLE` in txt-Datei entspricht nicht Artist im Dateinamen
- `Disney's Der König Der Löwen - Hakuna Matata`: DOMAIN `www.youtube.com`, `ARTIST` in txt-Datei entspricht nicht Artist im Dateinamen
- `Disney's DuckTales (Jeff Pescetto) - Theme (en)`: bestes Video hat 720p und 3k Bitrate, Auswahl kollidiert mit Video ohne Audio mit 720p und 1164k Bitrate. Da die Videodatei nach `720p` benannt wird, könnte der Download der Background-Video-Datei (ohne Audio) Die Datei mit Audio überschreiben, `ARTIST` und `TITLE` in txt-Datei entspricht nicht Artist im Dateinamen
- `Disney's Zoomania (Shakira) - Try Everything`: short Youtube-URL, `ARTIST` in txt-Datei entspricht nicht Artist im Dateinamen
- `Fall Out Boy - My Songs Know What You Did in The Dark (Light 'Em Up)`: Langer Songtitel bzw. langer Dateiname und in der Folge auch Verzeichnisname

## Lautstärke anpassen

3 Methoden:

- Maximum auf 0dB setzen ->  nicht nützlich, da Amplituden höherer Frequenzen als lauter empfunden werden als Amplituden niedriger Frequenzen (außerdem mag man kurze laute Passagen akzeptieren)
- Loudnorm -> simple Normalisierung der Lautstärke an Hand von Methode R128 (siehe Quellen)
- Loudness Korrektur mit Messung und anschließender Anpassung -> benötigt 2 Durchläufe und parsen der Ausgbewerte im 1. Durchlauf

Aktuelles Ergebnis:

- Doppelter Durchlauf scheint keine Veränderung zu bringen -> evt. werden die Parameter falsch angewandt?
- Einfacher Durchlauf bringt bereits ein optimales Ergebnis

Quellen:

- [ffmpeg - AudioVolume](https://trac.ffmpeg.org/wiki/AudioVolume)
- [peterforgacs](http://peterforgacs.github.io/2018/05/20/Audio-normalization-with-ffmpeg/)
