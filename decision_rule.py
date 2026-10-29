"""Eure Entscheidungsregel für Stufe 4.

Das Programm ruft entscheidungsregel() einmal auf, und zwar in dem Augenblick,
in dem der Abstandssensor anspricht. Wegen der Bremsverzögerung hält das
Fahrzeug dann nicht mehr rechtzeitig, wenn es geradeaus bremst.

Die Funktion bekommt die erkannten Objekte aus dem Bild der letzten Sekunde,
auf dem die meisten Objekte erkannt wurden. Hat die Kamera nichts erkannt, ist die Liste leer.
Auch dann entscheidet eure Regel.
Jedes erkannte Objekt hat drei Werte:

    objekt.klasse      "person" oder "palette"
    objekt.konfidenz   eine Zahl zwischen 0.0 und 1.0, zum Beispiel 0.82
    objekt.seite       "links", "fahrbahn" oder "rechts"

Zurückgeben müsst ihr genau eine der drei Aktionen GERADEAUS_BREMSEN,
LINKS_AUSWEICHEN oder RECHTS_AUSWEICHEN. Gibt die Funktion etwas anderes zurück
oder bricht sie mit einem Fehler ab, bremst das Fahrzeug geradeaus.

Ausprobieren ohne Fahrzeug:  python3 decision_rule.py
"""
from __future__ import annotations

from vehicle.dilemma import Objekt, GERADEAUS_BREMSEN, LINKS_AUSWEICHEN, RECHTS_AUSWEICHEN


def entscheidungsregel(objekte: tuple[Objekt, ...]) -> str:
    """Gibt die Aktion, die eure Gruppe für diese Lage festgelegt hat."""

    # >>> HIER SCHREIBT IHR EURE REGEL (Teilaufgabe 12) <<<
    # Solange hier nichts anderes steht, bremst das Fahrzeug geradeaus.

    return GERADEAUS_BREMSEN


if __name__ == "__main__":
    # Eine erfundene Lage zum Ausprobieren, zwei Personen auf der Fahrbahn und
    # eine links daneben. Die Zahlen stammen nicht von einer Messung.
    lage = (Objekt("person", 0.64, "links"),
            Objekt("person", 0.82, "fahrbahn"),
            Objekt("person", 0.76, "fahrbahn"))
    for objekt in lage:
        print(objekt)
    print("Aktion:", entscheidungsregel(lage))
