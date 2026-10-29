"""Die Datentypen des Projekts.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DetectedLine:
    """Ein erkannter Linienabschnitt in einer Bildzeile.

    start und end sind Spaltennummern, threshold ist der Otsu-Wert, aus dem sie
    berechnet wurden.
    """

    start: int
    end: int
    threshold: float

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"ende {self.end} liegt vor start {self.start}")

    @property
    def get_line_center(self) -> float:
        """Gibt die Spaltennummer der Linienmitte."""
        return (self.start + self.end) / 2

    @property
    def get_line_width(self) -> int:
        """Gibt die Breite des Streifens in Bildpunkten."""
        return self.end - self.start + 1

    def get_distance_from_center(self, bildbreite: int) -> float:
        """Gibt die Abweichung zur Bildmitte, -1 ganz links bis +1 ganz rechts."""
        soll = bildbreite / 2
        return (self.get_line_center - soll) / soll


@dataclass(frozen=True)
class Speed:
    """Das Tempo für beide Räder, jeweils zwischen 0.0 und 1.0.

    Ein Wert außerhalb des Bereichs löst einen Fehler aus.
    convert_to_allowed_speed_range() bringt einen Wert vorher in den Bereich.
    """

    speed_left: float
    speed_right: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.speed_left <= 1.0):
            raise ValueError(f"tempo_links ist {self.speed_left}, erlaubt ist 0.0 bis 1.0")
        if not (0.0 <= self.speed_right <= 1.0):
            raise ValueError(f"tempo_rechts ist {self.speed_right}, erlaubt ist 0.0 bis 1.0")

    @property
    def speed_is_zero(self) -> bool:
        """Gibt True, wenn beide Räder stillstehen."""
        return self.speed_left == 0.0 and self.speed_right == 0.0


STOP = Speed(0.0, 0.0)


@dataclass(frozen=True)
class RecognizedObject:
    """Ein erkanntes Objekt mit Name, Konfidenz und Kasten im Bild."""

    name: str
    confidence_score: float
    box: tuple[int, int, int, int]

    @property
    def get_object_label(self) -> str:
        """Gibt den Text für Bildbeschriftung und Dashboard."""
        return f"{self.name} {self.confidence_score:.2f}"


def convert_to_allowed_speed_range(wert: float) -> float:
    """Schneidet einen Wert auf den Bereich 0.0 bis 1.0 ab."""
    return min(1.0, max(0.0, wert))
