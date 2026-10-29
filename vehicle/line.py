"""Findet die Linie in einer Bildzeile."""
from __future__ import annotations

from typing import Sequence

import cv2
import numpy as np

from vehicle.datatypes import DetectedLine

# Ausgewertete Bildzeile, anteilig an der Bildhöhe. 0.8 ist das untere Fünftel.
SCAN_ROW_RATIO = 0.8
# Die Otsu-Schwelle wird nur aus dem Bildbereich unterhalb dieser Höhe berechnet.
# 0.6 heißt die unteren 40 Prozent des Bildes.
BAND_ANTEIL = 0.6

# Schmalere Streifen gelten als Rauschen.
MIN_LINE_WIDTH_PX = 15

# Breitere Streifen sind keine Linie, etwa bei starker Unterbelichtung. Nicht zu
# klein wählen, in Kurven wird das Klebeband über 100 Bildpunkte breit.
MAX_LINE_WIDTH_PX = 200


def find_all_strips(dark_columns: Sequence[int]) -> list[tuple[int, int]]:
    """Gibt alle zusammenhängenden Blöcke als Paare aus Anfang und Ende.

    Benachbarte Spalten mit Differenz 1 gehören zum selben Streifen, größere
    Differenzen sind Lücken. dark_columns muss aufsteigend sortiert sein,
    np.where liefert es so.
    """
    if len(dark_columns) == 0:
        return []

    strips = []
    start = previous = dark_columns[0]

    for column in dark_columns[1:]:
        if column - previous != 1:
            strips.append((int(start), int(previous)))
            start = column
        previous = column

    strips.append((int(start), int(previous)))
    return strips


def strip_width(strip: tuple[int, int]) -> int:
    """Gibt die Breite eines Streifens in Bildpunkten."""
    return strip[1] - strip[0] + 1


def strip_darkness(scan_row: np.ndarray, strip: tuple[int, int]) -> float:
    """Gibt den mittleren Grauwert eines Streifens, kleiner heißt dunkler."""
    return float(scan_row[strip[0]:strip[1] + 1].mean())


def find_widest_strip(dark_columns: Sequence[int]) -> tuple[int, int]:
    """Gibt Anfang und Ende des längsten Blocks aufeinanderfolgender Spalten."""
    assert len(dark_columns) > 0

    return max(find_all_strips(dark_columns), key=strip_width)


def detect_line(grayscale_image: np.ndarray) -> DetectedLine | None:
    """Sucht die Linie als dunkelsten Streifen in einer Bildzeile.

    Die Otsu-Schwelle wird nur aus dem unteren Bildband bestimmt, weil Wand und
    Horizont den Wert sonst verschieben.
    Voraussetzung ist eine feste Belichtung, sonst rechnet Otsu für jedes Bild
    eine andere Schwelle.

    Von allen dunklen Streifen gewinnt der dunkelste.
    Ein Schatten ist breit, aber nur mäßig dunkel, das Klebeband ist schmal und
    sehr dunkel. Bei gleicher Dunkelheit entscheidet die Breite.

    Gibt None zurück, wenn kein Streifen breit genug ist.
    Wirft ValueError, wenn ein Farbbild übergeben wird.
    """
    if grayscale_image.ndim != 2:
        raise ValueError(f"Graustufenbild erwartet, bekam {grayscale_image.ndim} Dimensionen")

    height = grayscale_image.shape[0]
    band = grayscale_image[int(height * BAND_ANTEIL):, :]
    threshold, _ = cv2.threshold(band, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    scan_row = grayscale_image[int(height * SCAN_ROW_RATIO)]
    dark_columns = np.where(scan_row <= threshold)[0]
    if dark_columns.size == 0:
        return None

    candidates = [strip for strip in find_all_strips(dark_columns)
                  if MIN_LINE_WIDTH_PX <= strip_width(strip) <= MAX_LINE_WIDTH_PX]
    if not candidates:
        return None

    start, end = min(candidates,
                     key=lambda strip: (strip_darkness(scan_row, strip), -strip_width(strip)))
    return DetectedLine(start=start, end=end, threshold=float(threshold))
