"""Liest den Abstandssensor."""

from gpiozero import DistanceSensor

ECHO_PIN = 24
TRIGGER_PIN = 25
MAX_DISTANCE_M = 4.0


class UltrasonicSensor:
    """Liest den Ultraschallsensor HC-SR04 und meldet, ob ein Hindernis zu nah ist.

    Zu nah heißt näher als der Halteabstand stopping_distance in Zentimetern.
    """

    def __init__(self, stopping_distance_cm: float) -> None:
        if stopping_distance_cm <= 0:
            raise ValueError(f"stopping_distance ist {stopping_distance_cm}, erlaubt ist ueber 0")

        self._sensor = DistanceSensor(echo=ECHO_PIN, trigger=TRIGGER_PIN,
                                        max_distance=MAX_DISTANCE_M)
        self._stopping_distance_cm = stopping_distance_cm

    def get_distance_cm(self) -> float:
        """Gibt den aktuellen Abstand in Zentimetern."""
        return self._sensor.distance * 100

    def is_too_close(self) -> bool:
        """Gibt True, wenn etwas näher steht als der erlaubte Halteabstand."""
        return self.get_distance_cm() < self._stopping_distance_cm

    def close(self) -> None:
        """Gibt die GPIO-Pins frei."""
        self._sensor.close()
