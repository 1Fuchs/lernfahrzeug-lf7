"""Speichert die Daten, die Steuerung und Webserver gemeinsam nutzen.

Dazu gehören das letzte Kamerabild, Linie, Abstand, erkannte Objekte und die
Freigabe aus dem Browser.
"""
from __future__ import annotations

import json
import threading
from time import monotonic

import cv2

from vehicle.datatypes import DetectedLine

TURN_REQUEST_TIMEOUT_S = 0.6


class SharedCache:
    """Speichert die gemeinsam genutzten Daten und schützt sie mit einem Lock.

    Das Lock verhindert, dass Steuerung und Webserver gleichzeitig auf dieselben
    Daten zugreifen.

    Das Lock gibt es nur in dieser Klasse, alle Zugriffe laufen über ihre
    Methoden.

    Keine Methode ruft eine andere Methode dieser Klasse auf. Ein
    threading.Lock kann vom selben Thread nicht zweimal gesperrt werden, das
    Programm würde sonst stehenbleiben.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jpeg: bytes | None = None
        self._detected_line: DetectedLine | None = None
        self._objects: tuple = ()
        self._distance_cm = 0.0
        self._go_signal = False
        self._running = True
        self._error: str | None = None
        self._turn_direction: str | None = None
        self._turn_stamp = 0.0
        self._decision: dict | None = None

    @property
    def is_running(self) -> bool:
        """Gibt True, solange das Programm weiterlaufen soll."""
        with self._lock:
            return self._running

    @property
    def has_starting_permission(self) -> bool:
        """Gibt True, wenn im Browser Starten gedrückt wurde."""
        with self._lock:
            return self._go_signal

    def set_image_result(self, image, line: DetectedLine | None, abstand_cm: float,
                         objects: tuple = ()) -> None:
        """Wandelt das Kamerabild in ein JPEG um und legt es mit Linie, Objekten
        und Abstand im geteilten Speicher ab.

        Das Kodieren geschieht vor der Sperre, damit der Webserver nicht warten muss.
        """
        jpg, buffer = cv2.imencode(".jpg", image)
        byte_stream = buffer.tobytes() if jpg else None

        with self._lock:
            self._detected_line = line
            self._objects = objects
            self._distance_cm = abstand_cm
            if byte_stream is not None:
                self._jpeg = byte_stream

    def cancel_driving(self, text: str) -> None:
        """Vermerkt, dass die Steuerung mit einem Fehler abgebrochen ist, und sperrt die Fahrt.

        Ohne diesen Vermerk zeigt das Dashboard weiter das letzte Bild und das
        Fahrzeug sieht im Browser lebendig aus, obwohl es nichts mehr entscheidet.
        """
        with self._lock:
            self._error = text
            self._go_signal = False

    @property
    def turn_request(self) -> str | None:
        """Gibt "links" oder "rechts", solange der Knopf im Browser gehalten wird.

        Der Wunsch verfällt nach TURN_REQUEST_TIMEOUT_S von allein. Ohne diese
        Frist würde sich das Fahrzeug weiterdrehen, wenn der Browser während
        des Haltens abstürzt oder das Loslassen nicht ankommt.
        """
        with self._lock:
            if self._turn_direction is None:
                return None
            if monotonic() - self._turn_stamp > TURN_REQUEST_TIMEOUT_S:
                return None
            return self._turn_direction

    def set_turn_request(self, richtung: str | None) -> None:
        """Nimmt den Drehwunsch aus dem Browser entgegen."""
        with self._lock:
            self._turn_direction = richtung
            self._turn_stamp = monotonic()

    def set_decision(self, decision: dict | None) -> None:
        """Legt die zuletzt gewählte Aktion der Stufe 4 mit ihren Eingaben ab.

        None heißt, es gibt keine Entscheidung anzuzeigen. Das ist in den
        Stufen 1 bis 3 immer so, deshalb bleibt das Feld dort ausgeblendet.
        """
        with self._lock:
            self._decision = decision

    def set_drive_control(self, frei: bool) -> None:
        """Gibt die Fahrt frei oder sperrt sie.

        Ein gemeldeter Fehler lässt sich nicht durch eine Freigabe übergehen.
        Eine Freigabe beendet außerdem jeden laufenden Drehwunsch, gedreht wird
        nur im Stillstand.
        """
        with self._lock:
            self._go_signal = frei and self._error is None
            if self._go_signal:
                self._turn_direction = None

    def set_stop_signal(self) -> None:
        """Gibt allen Threads das Signal, sich zu beenden."""
        with self._lock:
            self._running = False
            self._go_signal = False

    def get_image(self) -> bytes | None:
        """Gibt das zuletzt gespeicherte Kamerabild als JPEG, oder None vor dem ersten Bild."""
        with self._lock:
            return self._jpeg

    def get_status_json(self) -> bytes:
        """Gibt den Zustand als JSON für das Dashboard.

        Enthält die Konfidenzwerte, weil die Prüfkriterien der Stufen 2 und 3
        verlangen, dass die Lernenden sie vergleichen können.
        """
        with self._lock:
            inhalt = {
                "fahrt_frei": self._go_signal,
                "laeuft": self._running,
                "fehler": self._error,
                "abstand_cm": round(self._distance_cm, 1),
                "linienmitte": None if self._detected_line is None else round(self._detected_line.get_line_center, 1),
                "linienbreite": None if self._detected_line is None else self._detected_line.get_line_width,
                "objekte": [{"name": f.name, "konfidenz": round(f.confidence_score, 2)}
                          for f in self._objects],
                "entscheidung": self._decision,
            }
        return json.dumps(inhalt).encode("utf-8")
