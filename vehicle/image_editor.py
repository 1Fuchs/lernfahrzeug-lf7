"""Zeichnet in das Kamerabild, was das Programm erkannt hat."""
from __future__ import annotations

import cv2

from vehicle.datatypes import DetectedLine

# Farben in der Reihenfolge Blau, Grün, Rot, so erwartet OpenCV sie.
LINE_COLOR = (0, 255, 255)
STRIPE_COLOR = (0, 255, 0)
CENTER_COLOR = (0, 0, 255)
BOX_COLOR = (0, 255, 0)
TEXT_COLOR = (255, 255, 255)

FONT = cv2.FONT_HERSHEY_SIMPLEX

def draw_line(picture, line: DetectedLine | None, scan_row_ratio: float) -> None:
    """Zeichnet ausgewertete Zeile, gefundenen Streifen und Mitte ins Bild.

    Malt direkt in das übergebene Bild. Die ausgewertete Zeile wird immer
    gezeichnet, damit sichtbar ist, welchen Teil des Bildes das Programm auswertet.
    """
    height, width = picture.shape[:2]
    row_y = int(height * scan_row_ratio)

    cv2.line(picture, (0, row_y), (width, row_y), LINE_COLOR, 1)
    if line is None:
        cv2.putText(picture, "keine Linie", (8, 20), FONT, 0.5, CENTER_COLOR, 1)
        return

    cv2.line(picture, (line.start, row_y), (line.end, row_y), STRIPE_COLOR, 3)
    cv2.line(picture, (int(line.get_line_center), row_y - 12),
             (int(line.get_line_center), row_y + 12), CENTER_COLOR, 2)


def draw_box(bild, objekte) -> None:
    """Zeichnet einen Kasten mit Beschriftung um jedes erkannte Objekt."""
    for objekt in objekte:
        x1, y1, x2, y2 = objekt.box
        cv2.rectangle(bild, (x1, y1), (x2, y2), BOX_COLOR, 2)
        cv2.putText(bild, objekt.get_object_label, (x1, y1 - 8), FONT, 0.5, TEXT_COLOR, 1)

def draw_command(bild, text: str, start_drive: bool) -> None:
    """Schreibt FAHRT oder STOPP und eine Zeile Text ins Bild."""
    height = bild.shape[0]
    cv2.putText(bild, text, (8, 38), FONT, 0.45, TEXT_COLOR, 1)
    cv2.putText(bild, "START" if start_drive else "STOPP", (8, height - 10),
                FONT, 0.5, STRIPE_COLOR if start_drive else CENTER_COLOR, 2)
