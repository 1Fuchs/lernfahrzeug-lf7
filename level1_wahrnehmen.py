"""Stufe 1 Wahrnehmen: Das Fahrzeug folgt einer Linie nach einer festen Regel, ohne KI-Modell.

Die Regel steht in detect_line() in vehicle/line.py.

Aufruf im Browser: http://lernfahrzeug.local:8000
Abbruch mit Strg+C.
"""

import threading

import cv2

from vehicle import image_editor, dashboard, camera, line, level
from vehicle.distance import UltrasonicSensor
from vehicle.wheels import Wheels
from vehicle.line import detect_line
from vehicle.motor_speed_calc import determine_speed
from vehicle.cache import SharedCache

LEVEL = level.WAHRNEHMEN
PORT = 8000

# Tempo beim Drehen auf der Stelle über die Knöpfe im Browser.
TURN_SPEED = 0.7


def drive_car(camera_device, wheels: Wheels, distance: UltrasonicSensor,
              cache: SharedCache) -> None:
    """Wertet die Kamerabilder aus und steuert die Motoren, bis das Programm beendet wird."""
    try:
        while cache.is_running:
            color_image = camera_device.capture_array()

            grayscale_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY)
            detected_line = detect_line(grayscale_image)
            zu_nah = distance.is_too_close()

            speed = determine_speed(detected_line, zu_nah, cache.has_starting_permission,
                                    camera.PICTURE_WIDTH, LEVEL)

            richtung = cache.turn_request
            if richtung is not None and not cache.has_starting_permission:
                wheels.turn_in_place(TURN_SPEED, richtung == "rechts")
                anzeige = f"drehen {richtung}"
            else:
                wheels.drive(speed)
                anzeige = f"l {speed.speed_left:.2f}  r {speed.speed_right:.2f}"

            image_editor.draw_line(color_image, detected_line, line.SCAN_ROW_RATIO)
            image_editor.draw_command(color_image, anzeige, cache.has_starting_permission)
            cache.set_image_result(color_image, detected_line, distance.get_distance_cm())

    except Exception as problem:
        print(f"{type(problem).__name__}: {problem}")
        wheels.stop()
        cache.cancel_driving(f"{type(problem).__name__}: {problem}")


def main() -> None:
    wheels = Wheels()
    sensor = UltrasonicSensor(LEVEL.stopping_distance)
    cache = SharedCache()
    control_thread = None

    try:
        with camera.manage_camera() as cam:
            control_thread = threading.Thread(
                target=drive_car, args=(cam, wheels, sensor, cache),
                daemon=True)
            control_thread.start()

            print(f"Bereit auf http://lernfahrzeug.local:{PORT}")
            print("Abbruch mit Strg+C.\n")
            dashboard.start_server(cache, PORT)

    except KeyboardInterrupt:
        print("\nAbgebrochen.")

    finally:
        cache.set_stop_signal()
        if control_thread is not None:
            control_thread.join(timeout=1.0)
        wheels.stop()
        sensor.close()


if __name__ == "__main__":
    main()
