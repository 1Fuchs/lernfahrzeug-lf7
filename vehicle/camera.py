"""Öffnet und schließt die Kamera."""

from contextlib import contextmanager
from time import sleep

from picamera2 import Picamera2

# Kleines Bild für mehr Bilder pro Sekunde. Für die Linie reicht es.
PICTURE_WIDTH = 320
PICTURE_HEIGHT = 240

# Zeit, bis Belichtung und Weißabgleich eingependelt sind.
CAMERA_STABILIZATION_TIME_S = 2.0

# Feste Belichtung, an das Licht im Raum anpassen. EXPOSURE_TIME in
# Mikrosekunden, ANALOGUE_GAIN entspricht etwa der ISO-Zahl.
EXPOSURE_TIME = 24000
ANALOGUE_GAIN = 2.0


@contextmanager
def manage_camera(width: int = PICTURE_WIDTH, height: int = PICTURE_HEIGHT):
    """Öffnet die Kamera und gibt sie am Ende in jedem Fall frei.

    Die feste Belichtung wird erst nach der Einschwingzeit gesetzt, vorher
    übernimmt die Kamera die Werte nicht.
    """
    camera = Picamera2()
    try:
        camera.configure(camera.create_video_configuration(
            main={"size": (width, height), "format": "RGB888"}))
        camera.start()
        sleep(CAMERA_STABILIZATION_TIME_S)

        camera.set_controls({"AeEnable": False,
                             "ExposureTime": EXPOSURE_TIME,
                             "AnalogueGain": ANALOGUE_GAIN})
        sleep(1.0)

        yield camera
    finally:
        camera.stop()
        camera.close()
