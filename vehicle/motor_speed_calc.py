"""Rechnet aus der erkannten Linie das Tempo der beiden Räder aus."""
from __future__ import annotations

from vehicle.level import LevelSettings
from vehicle.datatypes import STOP, Speed, DetectedLine, RecognizedObject, convert_to_allowed_speed_range

# Name der Palettenklasse. Er muss genau so geschrieben sein wie beim Labeln,
# sonst wird das Fahrzeug auch an Paletten langsamer.
PALETTE_CLASS = "palette"


def calculate_speed(line: DetectedLine | None, picture_width: int,
                    level: LevelSettings) -> Speed:
    """Verteilt die Abweichung auf die beiden Räder.

    Ohne Linienfund wird angehalten. Sonst wird die Abweichung mit
    propotional_steering_adjustment verstärkt. Liegt die Linie rechts, dreht
    das linke Rad schneller. Werte unter 0.0 werden hier abgeschnitten, weil an
    dieser Stelle feststeht, dass ein Rad stehenbleiben darf.
    """
    if line is None:
        return STOP

    adjustment = level.propotional_steering_adjustment * line.get_distance_from_center(picture_width)
    return Speed(convert_to_allowed_speed_range(level.default_speed + adjustment),
                 convert_to_allowed_speed_range(level.default_speed - adjustment))

def determine_speed(detected_line: DetectedLine | None, too_close: bool, driving_enabled: bool,
                    picture_width: int, level: LevelSettings) -> Speed:
    """Entscheidet, was das Fahrzeug im nächsten Augenblick tut.

    Meldet der Abstandssensor ein Hindernis, hält das Fahrzeug, auch wenn die
    Fahrt freigegeben ist. Ist die Fahrt nicht freigegeben, hält es auch bei
    erkannter Linie. Nur wenn beides passt, folgt es der Linie.

    Gibt immer einen Fahrbefehl zurück, im Zweifel STOP.
    """
    if too_close:
        return STOP
    if not driving_enabled:
        return STOP
    return calculate_speed(detected_line, picture_width, level)


def is_caution_needed(objects: tuple[RecognizedObject, ...], level: LevelSettings) -> bool:
    """Gibt True, wenn das Fahrzeug wegen der erkannten Objekte langsamer werden soll.

    Ohne erkannte Objekte gibt es False. Ist level.palette_min_confidence None, gibt jedes
    Objekt True. Sonst gibt es nur dann False, wenn alle Objekte Paletten mit einer
    Konfidenz ab der Schwelle sind. Eine Person, eine unsichere Palette oder
    eine andere Klasse geben True.
    """
    if not objects:
        return False
    if level.palette_min_confidence is None:
        return True
    for found in objects:
        if found.name != PALETTE_CLASS:
            return True
        if found.confidence_score < level.palette_min_confidence:
            return True
    return False
