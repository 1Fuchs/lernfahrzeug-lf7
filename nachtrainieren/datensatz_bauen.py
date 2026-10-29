"""Baut aus den eigenen Palettenbildern und den COCO-Personen den Trainingsdatensatz.

Aufruf:
    python datensatz_bauen.py BILDORDNER LABELORDNER ANZAHL_VALIDIERUNG

BILDORDNER    die eigenen Fotos, so wie sie in Label Studio hochgeladen wurden
LABELORDNER   der Ordner labels aus dem YOLO-Export von Label Studio
ANZAHL_VALIDIERUNG  Anzahl der Bilder die in die Validierung sollen (Ausgehend vom Dateinamen)

Ergebnis ist der Ordner datensatz mit den Dateien dataset.yaml (für das
Training) und personen.yaml (für den Vergleich der Personenerkennung).
"""

import re
import shutil
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
COCO = HIER / "coco_personen"
ZIEL = HIER / "datensatz"

# COCO gibt der Person die 0 vor, die Palette bekommt deshalb die 1.

PALETTE = 1


def kopiere_paletten(bilder, labels, anzahl_val):
    # Label Studio setzt vor jeden Dateinamen ein Kürzel wie "6b3fcbec-".
    label_zu_bild = {}
    for label in labels.glob("*.txt"):
        name = re.sub(r"^[0-9a-f]{8}-", "", label.stem)
        label_zu_bild[name] = label

    fotos = sorted(f for f in bilder.iterdir()
                   if f.suffix.lower() in (".jpg", ".jpeg", ".png"))
    for nummer, foto in enumerate(fotos):
        teil = "val" if nummer < anzahl_val else "train"
        shutil.copy(foto, ZIEL / "images" / teil / foto.name)
        ziel_label = ZIEL / "labels" / teil / (foto.stem + ".txt")
        label = label_zu_bild.get(foto.stem)
        if label is None:
            print("ohne Label, gilt als Bild ohne Palette:", foto.name)
            ziel_label.write_text("")
            continue
        zeilen = [str(PALETTE) + zeile[1:] if zeile[:1] == "0" else zeile
                  for zeile in label.read_text().splitlines() if zeile.strip()]
        ziel_label.write_text("\n".join(zeilen) + "\n")
    return len(fotos)


def kopiere_personen():
    # Jedes fünfte Bild geht in die Validierung.
    personen_val = []
    bilder = sorted(COCO.glob("images/*/*.jpg"))
    for nummer, bild in enumerate(bilder, start=1):
        teil = "val" if nummer % 5 == 0 else "train"
        ziel_bild = ZIEL / "images" / teil / bild.name
        shutil.copy(bild, ziel_bild)
        label = COCO / "labels" / bild.parent.name / (bild.stem + ".txt")
        shutil.copy(label, ZIEL / "labels" / teil / label.name)
        if teil == "val":
            personen_val.append(str(ziel_bild))
    (ZIEL / "personen_val.txt").write_text("\n".join(personen_val) + "\n")
    return len(bilder)


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    bilder, labels, anzahl_val = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
    if not COCO.exists():
        sys.exit("Ordner coco_personen fehlt. Zuerst personen_laden.py ausführen.")

    for teil in ("train", "val"):
        (ZIEL / "images" / teil).mkdir(parents=True, exist_ok=True)
        (ZIEL / "labels" / teil).mkdir(parents=True, exist_ok=True)

    n_paletten = kopiere_paletten(bilder, labels, anzahl_val)
    n_personen = kopiere_personen()

    namen = "names:\n  0: person\n  1: palette\n"
    (ZIEL / "dataset.yaml").write_text(
        f"path: {ZIEL.as_posix()}\ntrain: images/train\nval: images/val\n" + namen)
    (ZIEL / "personen.yaml").write_text(
        f"path: {ZIEL.as_posix()}\ntrain: personen_val.txt\nval: personen_val.txt\n" + namen)

    print(f"{n_paletten} eigene Bilder, {n_personen} COCO-Bilder, fertig in {ZIEL}")


if __name__ == "__main__":
    main()
