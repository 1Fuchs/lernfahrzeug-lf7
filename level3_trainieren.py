"""Stufe 3 Trainieren: Ein selbst nachtrainiertes Modell wird eingebunden.

Gegenüber Stufe 2 ändert sich an diesem Programm nichts außer einer Zeile,
nämlich welches Profil geladen wird. Das Profil TRAINIEREN in vehicle/level.py
bringt das eigene Modell und die Palettenschwelle mit. Die Fahrlogik, die
Regelung, der Halt am Abstandssensor und die Anzeige sind unverändert.

Was das Fahrzeug erkennen kann, bestimmen die Trainingsdaten. Wer eine neue
Klasse braucht, erhebt und labelt Bilder, der Code bleibt gleich.

Das Modell palette_v1.pt kennt zwei Klassen, 0 person und 1 palette.

Aufruf im Browser: http://lernfahrzeug.local:8000
Abbruch mit Strg+C.
"""

import threading
from time import monotonic

import cv2

from vehicle import image_editor, dashboard, camera, line, level
from vehicle.distance import UltrasonicSensor
from vehicle.wheels import Wheels
from vehicle.line import detect_line
from vehicle.model import ObjectIdentifier
from vehicle.motor_speed_calc import determine_speed, is_caution_needed
from vehicle.datatypes import Speed, convert_to_allowed_speed_range
from vehicle.cache import SharedCache

LEVEL = level.TRAINIEREN
PORT = 8000

# Tempo beim Drehen auf der Stelle über die Knöpfe im Browser.
TURN_SPEED = 0.7

# Die Objekterkennung läuft nur in jedem N-ten Kamerabild. Sie ist langsam,
# und die Linienverfolgung soll trotzdem schnell reagieren.
DETECTION_INTERVALL = 4

# Auf dieses Tempo wird das Fahrzeug langsamer, wenn ein Objekt erkannt wird.
# Unter etwa 0.45 fährt das Fahrzeug nicht an.
DETECTION_SPEED = 0.5

# Erst wenn ein Objekt so viele Sekunden ohne Unterbrechung erkannt wird,
# wird das Fahrzeug langsamer.
DETECTION_HOLD_S = 1.0

# So viele Sekunden darf das Objekt in der Erkennung fehlen, ohne dass die
# Zeit für DETECTION_HOLD_S von vorn beginnt.
DETECTION_GAP_S = 0.5


def reduce_speed_on_detection(drive_command: Speed, slow_down: bool) -> Speed:
    """Senkt das Tempo auf DETECTION_SPEED, wenn slow_down True ist.

    Ob ein Objekt lange genug erkannt wurde, entscheidet drive_car(). Diese
    Funktion rechnet nur das neue Tempo aus. Der Unterschied zwischen linkem und
    rechtem Rad bleibt erhalten, damit das Fahrzeug weiter der Linie folgt.
    Steht das Fahrzeug, weil der Abstandssensor angesprochen hat oder die Fahrt
    nicht freigegeben ist, bleibt es stehen.
    """
    if not slow_down:
        return drive_command
    if drive_command.speed_is_zero:
        return drive_command
    middle = (drive_command.speed_left + drive_command.speed_right) / 2
    difference = drive_command.speed_left - middle
    return Speed(convert_to_allowed_speed_range(DETECTION_SPEED + difference),
                 convert_to_allowed_speed_range(DETECTION_SPEED - difference))


def drive_car(camera_device, wheels: Wheels, distance: UltrasonicSensor,
              object_detector: ObjectIdentifier, cache: SharedCache) -> None:

    """Wertet die Kamerabilder aus und steuert die Motoren, bis das Programm beendet wird."""
    frame_count = 0
    objects: tuple = ()
    seen_since: float | None = None
    last_seen = 0.0
    was_free = False

    try:
        while cache.is_running:
            frame_count = frame_count + 1
            color_image = camera_device.capture_array()

            if frame_count % DETECTION_INTERVALL == 0:
                objects = object_detector.get_object_list(color_image)

            grayscale_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY)
            detected_line = detect_line(grayscale_image)

            drive_command = determine_speed(detected_line, distance.is_too_close(), cache.has_starting_permission,
                                            camera.PICTURE_WIDTH, LEVEL)
            free_now = cache.has_starting_permission
            if free_now and not was_free:
                seen_since = None
                last_seen = 0.0
            was_free = free_now

            now = monotonic()
            if is_caution_needed(objects, LEVEL):
                last_seen = now
                if seen_since is None:
                    seen_since = now
            elif now - last_seen > DETECTION_GAP_S:
                seen_since = None

            slow_down = seen_since is not None and now - seen_since >= DETECTION_HOLD_S
            drive_command = reduce_speed_on_detection(drive_command, slow_down)

            richtung = cache.turn_request
            if richtung is not None and not cache.has_starting_permission:
                wheels.turn_in_place(TURN_SPEED, richtung == "rechts")
                anzeige = f"drehen {richtung}"
            else:
                wheels.drive(drive_command)
                anzeige = f"l {drive_command.speed_left:.2f}  r {drive_command.speed_right:.2f}"

            image_editor.draw_line(color_image, detected_line, line.SCAN_ROW_RATIO)
            image_editor.draw_box(color_image, objects)
            image_editor.draw_command(color_image, anzeige, cache.has_starting_permission)
            cache.set_image_result(color_image, detected_line, distance.get_distance_cm(), objects)

    except Exception as problem:
        print(f"{type(problem).__name__}: {problem}")
        wheels.stop()
        cache.cancel_driving(f"{type(problem).__name__}: {problem}")


def main() -> None:
    wheels = Wheels()
    sensor = UltrasonicSensor(LEVEL.stopping_distance)
    # Das Modell rechnet auf 320 Bildpunkten, so groß wie das Kamerabild.
    object_detector = ObjectIdentifier(LEVEL.model_path, LEVEL.confidence_threshold,
                                       image_size=camera.PICTURE_WIDTH)
    cache = SharedCache()
    control_thread = None

    try:
        with camera.manage_camera() as cam:
            control_thread = threading.Thread(
                target=drive_car,
                args=(cam, wheels, sensor, object_detector, cache),
                daemon=True)
            control_thread.start()

            print(f"Bereit auf http://lernfahrzeug.local:{PORT}")
            print(f"Modell {LEVEL.model_path}, Schwelle {LEVEL.confidence_threshold}")
            print("Abbruch mit Strg+C.\n")
            dashboard.start_server(cache, PORT)

    except KeyboardInterrupt:
        print("\nAbgebrochen.")

    finally:
        cache.set_stop_signal()
        if control_thread is not None:
            control_thread.join(timeout=1.0)
        wheels.close()
        sensor.close()


if __name__ == "__main__":
    main()
