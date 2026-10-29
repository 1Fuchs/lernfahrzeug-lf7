"""Die Werte, die sich von Stufe zu Stufe unterscheiden."""
from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class LevelSettings:
    """Hält die Einstellungen einer Stufe.

    model_path ist None, solange keine Objekterkennung beteiligt ist.

    palette_min_confidence ist None, solange keine Schwelle eingetragen ist.
    Dann wird das Fahrzeug bei jedem erkannten Objekt langsamer.

    brake_delay_s wird nur vom Programm der Stufe 4 gelesen. In den Stufen 1
    bis 3 bleibt es 0.0, dort hält das Fahrzeug sofort, wenn der Abstandssensor
    anspricht.
    """

    default_speed: float
    propotional_steering_adjustment: float
    stopping_distance: float
    model_path: str | None = None
    confidence_threshold: float = 0.5
    palette_min_confidence: float | None = None
    brake_delay_s: float = 0.0

    def __post_init__(self) -> None:
        if not (0.0 < self.default_speed <= 1.0):
            raise ValueError(f"basistempo ist {self.default_speed}, erlaubt ist ueber 0.0 bis 1.0")
        if self.propotional_steering_adjustment <= 0.0:
            raise ValueError(f"kp ist {self.propotional_steering_adjustment}, erlaubt ist ueber 0.0")
        if self.stopping_distance <= 0.0:
            raise ValueError(f"halt_abstand_cm ist {self.stopping_distance}, erlaubt ist ueber 0.0")
        if self.palette_min_confidence is not None and not (0.0 < self.palette_min_confidence <= 1.0):
            raise ValueError(f"palette_min_confidence ist {self.palette_min_confidence}, "
                             f"erlaubt ist None oder über 0.0 bis 1.0")
        if self.brake_delay_s < 0.0:
            raise ValueError(f"brake_delay_s ist {self.brake_delay_s}, erlaubt ist ab 0.0")


# Stufe 1, ohne Modell.
# default_speed: unter etwa 0.45 fährt das Fahrzeug nicht an.
# stopping_distance: Halteabstand in cm, an der Teststrecke einstellen.
WAHRNEHMEN = LevelSettings(default_speed=0.6, propotional_steering_adjustment=0.4, stopping_distance=18.0)

# Stufe 2 ist Stufe 1 mit einem vortrainierten Modell.
ERKENNEN = replace(WAHRNEHMEN, model_path="yolov8n.pt")

# Stufe 3 ist Stufe 2 mit einem selbst nachtrainierten Modell.
#
# >>> HIER TRAGT IHR EIN (Teilaufgabe 11) <<<
# model_path: Ersetzt "palette_v1.pt" durch den Dateinamen eures eigenen
#   Modells. Legt die Datei in denselben Ordner wie palette_v1.pt.
# palette_min_confidence: Ersetzt None durch eine Zahl, zum Beispiel 0.8.
#   Ab dieser Konfidenz gilt eine Palette als sicher erkannt, und das
#   Fahrzeug behält sein Tempo, solange keine Person im Bild ist.
#   Bei None wird es bei jedem Objekt langsamer.
#
# Beide Werte gelten auch in Stufe 4. Ihr tragt sie nur hier ein.
TRAINIEREN = replace(WAHRNEHMEN, model_path="palette_v1.pt",
                     palette_min_confidence=None)


# Stufe 4 ist Stufe 3 mit Bremsverzögerung. Modell und Palettenschwelle kommen
# aus TRAINIEREN.
# stopping_distance 40 cm nicht ändern.
# brake_delay_s an der Teststrecke einstellen. In dieser Zeit muss das Fahrzeug
# weiter als 40 cm fahren, sonst hält es vor der Figur.
VERANTWORTEN = replace(TRAINIEREN, brake_delay_s=1.0, stopping_distance=40.0)
