"""Erkennt Objekte im Bild und liefert sie als einfache Werte."""

from ultralytics import YOLO

from vehicle.datatypes import RecognizedObject


def build_box_classifier(box, name: dict[int, str]) -> RecognizedObject:
    """Wandelt ein Ergebnis von Ultralytics in ein RecognizedObject um.

    cls und conf kommen als Tensor, xyxy hat die Form (1, 4). Diese Umrechnung
    steht nur hier, damit der Rest des Projekts mit einfachen Python-Werten
    arbeitet.
    """
    x1, y1, x2, y2 = (int(wert) for wert in box.xyxy[0])
    return RecognizedObject(name=name[int(box.cls)],
                            confidence_score=float(box.conf),
                            box=(x1, y1, x2, y2))


class ObjectIdentifier:
    """Lädt ein YOLO-Modell und liefert Erkennungen für ein Bild."""

    def __init__(self, modell_pfad: str, konfidenz_schwelle: float,
                 image_size: int | None = None) -> None:
        """Lädt das Modell.

        image_size ist die Kantenlänge, auf die das Modell das Bild bringt.
        None lässt Ultralytics seinen Standardwert nehmen, das sind 640
        Bildpunkte, unabhängig davon wie groß das Kamerabild ist.
        """
        if not modell_pfad:
            raise ValueError("modell_pfad darf nicht leer sein")
        self._modell = YOLO(modell_pfad)
        self._schwelle = konfidenz_schwelle
        self._image_size = image_size

    def get_object_list(self, bild) -> tuple[RecognizedObject, ...]:
        """Gibt alle erkannten Objekte, deren Konfidenz über der Schwelle liegt.

        Ultralytics gibt eine Liste zurück, auch für ein einzelnes Bild,
        deshalb [0]. verbose=False unterdrückt die Zusammenfassung. Das
        Ergebnis ist ein Tupel, damit zwei Threads es gefahrlos lesen können.
        """
        zusatz = {} if self._image_size is None else {"imgsz": self._image_size}
        ergebnis = self._modell(bild, conf=self._schwelle, verbose=False, **zusatz)[0]
        return tuple(build_box_classifier(k, ergebnis.names) for k in ergebnis.boxes)
