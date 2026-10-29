"""Stufe 4 Verantworten: Das Fahrzeug handelt nach der Entscheidungsregel der Gruppe.

An dieser Datei ändert ihr nichts. Eure Regel schreibt ihr in
decision_rule.py, euer Modell und die Palettenschwelle stehen im Profil
TRAINIEREN in vehicle/level.py.

Gegenüber Stufe 3 ist die Bremsverzögerung eingeschaltet. Spricht der
Abstandssensor an, ruft das Programm die Entscheidungsregel aus
decision_rule.py auf. Sie bekommt die erkannten Objekte aus dem Bild der letzten
Sekunde, auf dem die meisten Objekte erkannt wurden, jeweils mit der Seite links, Fahrbahn oder
rechts. Ist nichts erkannt, bekommt sie eine leere Liste. Sie wählt geradeaus
bremsen, links ausweichen oder rechts ausweichen. Beim Bremsen fährt das
Fahrzeug noch LEVEL.brake_delay_s lang weiter und hält deshalb nicht mehr
rechtzeitig. Nach der Aktion hält das Fahrzeug an und wartet auf eine neue
Freigabe im Browser. Die gewählte Aktion steht mit ihren Eingaben im
Dashboard.

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
from vehicle.dilemma import DilemmaControl, side_of

LEVEL = level.VERANTWORTEN
PORT = 8000

# Nur für die Lehrkraft. True nimmt beispielregel.py, die immer links ausweicht.
# Für die Gruppen bleibt der Wert False.
USE_EXAMPLE_RULE = False

if USE_EXAMPLE_RULE:
    from beispielregel import entscheidungsregel as rule
else:
    from decision_rule import entscheidungsregel as rule

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

    Wie in Stufe 2 und 3. Der Unterschied zwischen linkem und rechtem Rad bleibt
    erhalten.
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

    # NEU IN STUFE 4
    dilemma = DilemmaControl(rule, LEVEL.brake_delay_s, camera.PICTURE_WIDTH)

    try:
        while cache.is_running:
            frame_count = frame_count + 1
            color_image = camera_device.capture_array()

            if frame_count % DETECTION_INTERVALL == 0:
                objects = object_detector.get_object_list(color_image)

            grayscale_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY)
            detected_line = detect_line(grayscale_image)

            free_now = cache.has_starting_permission
            if free_now and not was_free:
                seen_since = None
                last_seen = 0.0
                dilemma.reset()              # NEU IN STUFE 4
                cache.set_decision(None)     # NEU IN STUFE 4
            was_free = free_now

            # NEU IN STUFE 4: Der Abstandssensor wird erst unten in dilemma.step() ausgewertet.
            drive_command = determine_speed(detected_line, False, free_now,
                                            camera.PICTURE_WIDTH, LEVEL)

            now = monotonic()
            if is_caution_needed(objects, LEVEL):
                last_seen = now
                if seen_since is None:
                    seen_since = now
            elif now - last_seen > DETECTION_GAP_S:
                seen_since = None

            slow_down = seen_since is not None and now - seen_since >= DETECTION_HOLD_S
            drive_command = reduce_speed_on_detection(drive_command, slow_down)

            # NEU IN STUFE 4
            step = dilemma.step(distance.is_too_close(), free_now, drive_command, objects, now)
            if step.decision is not None:
                cache.set_decision(step.decision)
                print(f"Entscheidung {step.decision}")
                print(f"    Abstand bei Auslösung {distance.get_distance_cm():.1f} cm")
                # Gibt jedes erkannte Objekt mit seiner Position im Bild im Terminal aus. Das hilft
                # beim Einstellen von LANE_HALF_WIDTH_PX in vehicle/dilemma.py.
                for found in objects:
                    x1, _, x2, _ = found.box
                    print(f"    Objekt {found.name} {found.confidence_score:.2f}  Mitte x {(x1 + x2) // 2}"
                          f"  {side_of(found.box, camera.PICTURE_WIDTH)}")
            if step.finished:
                cache.set_drive_control(False)

            richtung = cache.turn_request
            if step.text is None and richtung is not None and not free_now:
                wheels.turn_in_place(TURN_SPEED, richtung == "rechts")
                anzeige = f"drehen {richtung}"
            else:
                wheels.drive(step.command)
                anzeige = step.text or f"l {step.command.speed_left:.2f}  r {step.command.speed_right:.2f}"

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
            print(f"Bremsverzögerung {LEVEL.brake_delay_s} s, "
                  f"Regel aus {'beispielregel.py' if USE_EXAMPLE_RULE else 'decision_rule.py'}")
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
