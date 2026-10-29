# Modell auf die Klasse Palette nachtrainieren

## 1. Einrichten (einmalig)

    python -m venv venv

Umgebung aktivieren:

- macOS und Linux: `source venv/bin/activate`
- Windows: `venv\Scripts\activate`

Dann:

    pip install ultralytics label-studio fiftyone

Meldet pip Konflikte, Label Studio in einer zweiten Umgebung installieren.

## 2. Personenbilder laden (einmalig)

    python personen_laden.py

Legt den Ordner `coco_personen` mit 800 Bildern an. Sie sorgen dafür, dass das
Modell beim Nachtrainieren die Klasse Person nicht vergisst. Auch mit ihnen
sinkt die Personenerkennung messbar, das zeigt Schritt 7.

## 3. Fotos labeln

    label-studio start

Im Browser öffnet sich Label Studio unter `http://localhost:8080`.

1. Projekt anlegen, unter „Labeling Setup“ die Vorlage „Object Detection with
   Bounding Boxes“ wählen und als einziges Label `palette` eintragen.
2. Die eigenen Fotos hochladen und jede Palette mit einem Rahmen markieren.
   Bilder ohne Palette bleiben ohne Rahmen.
3. Über „Export“ das Format „YOLO“ wählen und die ZIP-Datei entpacken.
   Gebraucht wird nur der Ordner `labels`.

## 4. Datensatz bauen

    python datensatz_bauen.py ORDNER_MIT_FOTOS ORDNER_LABELS 50

Die Zahl am Ende gibt an, wie viele Fotos in die Validierung gehen. Genommen
werden die ersten Fotos in alphabetischer Reihenfolge der Dateinamen. Am besten
eine eigene Aufnahmeserie dafür nehmen, sonst stehen fast gleiche Bilder in
Training und Validierung.

## 5. Trainieren

    yolo detect train data=datensatz/dataset.hs=50 imgsz=320 batch=16

## 6. Modell aufs Fahrzeug bringen

1. `best.pt` umbenennen
2. Die Datei in den Code-Ordner neben `palette_v1.pt` legen.
3. In `vehicle/level.py` bei `TRAINIEREN` eintragen.

## 7. Personenerkennung vergleichen

    yolo val model=yolov8n.pt data=datensatz/personen.yaml classes=0 imgsz=320
    yolo val model=PFAD/ZU/best.pt data=daten=0 imgsz=320

