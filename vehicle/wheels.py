"""Steuert die beiden Motoren."""

from gpiozero import Motor

from vehicle.datatypes import STOP, Speed

# GPIO-Nummern der Motoren am DRV8833. Bei anderer Verkabelung hier ändern.
LEFT_FORWARD = 22
LEFT_BACKWARD = 23
RIGHT_FORWARD = 27
RIGHT_BACKWARD = 17


class Wheels:
    """Nimmt einen Fahrbefehl und setzt ihn auf die Motoren um."""

    def __init__(self) -> None:
        self._drive_left = Motor(forward=LEFT_FORWARD, backward=LEFT_BACKWARD)
        self._drive_right = Motor(forward=RIGHT_FORWARD, backward=RIGHT_BACKWARD)

    def drive(self, befehl: Speed) -> None:
        """Setzt beide Räder auf das Tempo im Befehl.

        Ein Befehl mit Tempo 0 hält beide Räder an.
        """
        if befehl.speed_is_zero:
            self._drive_left.stop()
            self._drive_right.stop()
        else:
            self._drive_left.forward(befehl.speed_left)
            self._drive_right.forward(befehl.speed_right)

    def turn_in_place(self, tempo: float, to_the_right: bool) -> None:
        """Dreht auf der Stelle, ein Rad vorwärts, das andere rückwärts.

        Das ist der einzige Weg rückwärts. Speed lässt nur Werte ab 0.0 zu,
        deshalb geht das nicht über drive().
        """
        if not (0.0 < tempo <= 1.0):
            raise ValueError(f"tempo ist {tempo}, erlaubt ist ueber 0.0 bis 1.0")

        if to_the_right:
            self._drive_left.forward(tempo)
            self._drive_right.backward(tempo)
        else:
            self._drive_left.backward(tempo)
            self._drive_right.forward(tempo)

    def stop(self) -> None:
        """Hält beide Räder an."""
        self.drive(STOP)

    def close(self) -> None:
        """Hält an und gibt die GPIO-Pins frei."""
        self.stop()
        self._drive_left.close()
        self._drive_right.close()
