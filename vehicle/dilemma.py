"""Steuert die Dilemmasituation in Stufe 4.

Das Lagebild ist die Liste der erkannten Objekte mit ihrer Seite links,
Fahrbahn oder rechts. Spricht der Abstandssensor an, bekommt die
Entscheidungsregel das Lagebild, und das Fahrzeug fährt die gewählte Aktion.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from vehicle.datatypes import STOP, RecognizedObject, Speed

# Die drei Aktionen, zwischen denen eine Entscheidungsregel wählt.
GERADEAUS_BREMSEN = "geradeaus bremsen"
LINKS_AUSWEICHEN = "links ausweichen"
RECHTS_AUSWEICHEN = "rechts ausweichen"
AKTIONEN = (GERADEAUS_BREMSEN, LINKS_AUSWEICHEN, RECHTS_AUSWEICHEN)

# Mögliche Werte für objekt.seite
LINKS = "links"
FAHRBAHN = "fahrbahn"
RECHTS = "rechts"

# An der Teststrecke einstellen. Halbe Breite der Fahrbahn um die Bildmitte in
# Bildpunkten. 55 ergibt die Fahrbahn 105 bis 215.
LANE_HALF_WIDTH_PX = 55

# An der Teststrecke einstellen. So viele Sekunden werden die Lagebilder
# aufgehoben, die Regel bekommt das mit den meisten Objekten, weil das Modell von
# Bild zu Bild Figuren verliert.
SCENE_MEMORY_S = 1.0

# Ausweichen, an der Teststrecke einstellen. Das Fahrzeug fährt EVADE_TURN_S
# Sekunden einen Bogen und danach EVADE_STRAIGHT_S Sekunden geradeaus.
EVADE_TURN_S = 0.25
EVADE_INNER_SPEED = 0.0
EVADE_OUTER_SPEED = 0.9
EVADE_STRAIGHT_S = 1.0
EVADE_STRAIGHT_SPEED = 0.6


@dataclass(frozen=True)
class Objekt:
    """Ein Objekt, wie es die Entscheidungsregel bekommt.

    klasse ist der Name aus dem Modell, etwa "person" oder "palette".
    konfidenz liegt zwischen 0.0 und 1.0. seite ist "links", "fahrbahn"
    oder "rechts".
    """

    klasse: str
    konfidenz: float
    seite: str


def side_of(box: tuple[int, int, int, int], picture_width: int) -> str:
    """Gibt "links", "fahrbahn" oder "rechts" für die Mitte eines Kastens."""
    x1, _, x2, _ = box
    center = (x1 + x2) / 2
    if center < picture_width / 2 - LANE_HALF_WIDTH_PX:
        return LINKS
    if center > picture_width / 2 + LANE_HALF_WIDTH_PX:
        return RECHTS
    return FAHRBAHN


def describe_scene(objects: Sequence[RecognizedObject], picture_width: int) -> tuple[Objekt, ...]:
    """Gibt alle erkannten Objekte mit Klasse, Konfidenz und Seite, sortiert von links nach rechts.

    Es zählt nur, ob ein Objekt links, auf der Fahrbahn oder rechts liegt. Wie
    hoch er im Bild steht, also wie weit entfernt, spielt keine Rolle. Ohne
    erkannte Objekte ist das Lagebild leer.
    """
    ordered = sorted(objects, key=lambda found: found.box[0])
    return tuple(Objekt(found.name, found.confidence_score, side_of(found.box, picture_width))
                 for found in ordered)


def decide_safely(rule: Callable[[tuple[Objekt, ...]], str],
                  scene: tuple[Objekt, ...]) -> tuple[str, str]:
    """Ruft die Entscheidungsregel auf und gibt Aktion und Hinweis.

    Bricht die Regel mit einem Fehler ab oder gibt sie etwas anderes als eine
    der drei Aktionen zurück, gilt GERADEAUS_BREMSEN, und der Hinweis nennt den
    Grund. Sonst ist der Hinweis leer.
    """
    try:
        action = rule(scene)
    except Exception as problem:
        return GERADEAUS_BREMSEN, f"Regel abgebrochen, {type(problem).__name__}: {problem}"
    if action not in AKTIONEN:
        return GERADEAUS_BREMSEN, f"Regel gab {action!r} zurück, erlaubt sind nur die drei Aktionen"
    return action, ""


def maneuver_command(action: str, elapsed_s: float, frozen_command: Speed,
                     brake_delay_s: float) -> Speed | None:
    """Gibt den Fahrbefehl während einer Aktion, oder None, wenn sie vorbei ist.

    Beim Bremsen fährt das Fahrzeug brake_delay_s lang mit dem Fahrbefehl weiter,
    der beim Ansprechen des Sensors galt. Das ist die Bremsverzögerung. Beim
    Ausweichen beginnt das Manöver sofort, ein Bogen und danach geradeaus, ohne
    Verzögerung und ohne Tempoabsenkung. Bei None hält das Programm an.
    """
    if action == GERADEAUS_BREMSEN:
        return frozen_command if elapsed_s < brake_delay_s else None

    if elapsed_s < EVADE_TURN_S:
        if action == LINKS_AUSWEICHEN:
            return Speed(EVADE_INNER_SPEED, EVADE_OUTER_SPEED)
        return Speed(EVADE_OUTER_SPEED, EVADE_INNER_SPEED)
    if elapsed_s < EVADE_TURN_S + EVADE_STRAIGHT_S:
        return Speed(EVADE_STRAIGHT_SPEED, EVADE_STRAIGHT_SPEED)
    return None


def build_decision(action: str, note: str, scene: tuple[Objekt, ...]) -> dict:
    """Gibt die Entscheidung so, wie das Dashboard sie anzeigt."""
    return {"aktion": action,
            "hinweis": note,
            "eingaben": [{"klasse": objekt.klasse,
                          "konfidenz": round(objekt.konfidenz, 2),
                          "seite": objekt.seite} for objekt in scene]}


@dataclass(frozen=True)
class Step:
    """Was das Programm der Stufe 4 in einem Durchlauf tun soll.

    command ist der Fahrbefehl. text ist None im normalen Fahrbetrieb, sonst die
    Zeile für das Kamerabild. decision ist nur in dem Durchlauf gesetzt, in dem
    die Regel gefragt wurde. finished heißt, die Aktion ist vorbei und die
    Freigabe im Browser wird zurückgenommen.
    """

    command: Speed
    text: str | None = None
    decision: dict | None = None
    finished: bool = False


class DilemmaControl:
    """Alles, was Stufe 4 vom Fahren in Stufe 3 unterscheidet.

    Spricht der Sensor an, fragt sie einmal die Entscheidungsregel und fährt
    danach die gewählte Aktion ab. Sie steuert keine Motoren und schreibt nicht
    in den Cache, sie sagt nur, was zu tun ist. Deshalb lässt sie sich ohne
    Raspberry Pi prüfen.
    """

    def __init__(self, rule: Callable[[tuple[Objekt, ...]], str],
                 brake_delay_s: float, picture_width: int) -> None:
        self._rule = rule
        self._brake_delay_s = brake_delay_s
        self._picture_width = picture_width
        self._action: str | None = None
        self._start = 0.0
        self._frozen = STOP
        self._armed = False
        self._recent: list[tuple[float, tuple[Objekt, ...]]] = []

    def reset(self) -> None:
        """Beim Druck auf Starten aufrufen.

        Danach muss der Abstandssensor einmal nichts gemeldet haben, bevor er
        eine Aktion auslösen kann. Sonst würde das Fahrzeug nach einem Start direkt vor der
        Figur die Verzögerung lang weiterfahren.
        """
        self._action = None
        self._armed = False
        self._recent = []

    def _fullest_scene(self, now: float) -> tuple[float, tuple[Objekt, ...]]:
        """Gibt Zeitpunkt und Lagebild mit den meisten Objekten.

        Bei gleich vielen Objekten gewinnt das jüngere. Ist kein Lagebild
        aufgehoben, gibt es ein leeres Lagebild mit dem Zeitpunkt now.
        """
        if not self._recent:
            return now, ()
        return max(self._recent, key=lambda entry: (len(entry[1]), entry[0]))

    def step(self, too_close: bool, free_now: bool, drive_command: Speed,
             objects: Sequence[RecognizedObject], now: float) -> Step:
        """Gibt den Schritt für diesen Durchlauf.

        drive_command ist der Fahrbefehl wie in Stufe 3, berechnet ohne den
        Sensor. Ohne Freigabe wird eine laufende Aktion abgebrochen. Steht das
        Fahrzeug nach dem Start schon zu nah, hält es sofort wie in Stufe 1.
        """
        if not free_now:
            self._action = None
            return Step(drive_command)
        if not too_close:
            self._armed = True

        decision = None
        if self._action is None:
            self._recent.append((now, describe_scene(objects, self._picture_width)))
            self._recent = [entry for entry in self._recent if now - entry[0] <= SCENE_MEMORY_S]

            if not too_close:
                return Step(drive_command)
            if not self._armed:
                return Step(STOP)
            seen_at, scene = self._fullest_scene(now)
            self._action, note = decide_safely(self._rule, scene)
            self._start = now
            self._frozen = drive_command
            age = f"Lagebild {now - seen_at:.1f} s alt"
            decision = build_decision(self._action, f"{note}; {age}" if note else age, scene)

        command = maneuver_command(self._action, now - self._start, self._frozen,
                                   self._brake_delay_s)
        if command is None:
            text = f"{self._action}, angehalten"
            self._action = None
            return Step(STOP, text, decision, finished=True)
        return Step(command,
                    f"{self._action}  l {command.speed_left:.2f}  r {command.speed_right:.2f}",
                    decision)
