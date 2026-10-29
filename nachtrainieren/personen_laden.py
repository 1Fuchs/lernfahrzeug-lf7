"""Lädt 800 Bilder mit Personen aus COCO 2017 samt Labels.

Die Bilder werden den eigenen Palettenaufnahmen beigemischt.
"""

import fiftyone as fo
import fiftyone.zoo as foz

daten = foz.load_zoo_dataset(
    "coco-2017",
    split="train",
    label_types=["detections"],
    classes=["person"],
    max_samples=800,
    only_matching=True,
)

daten.export(
    export_dir="./coco_personen",
    dataset_type=fo.types.YOLOv5Dataset,
    label_field="ground_truth",
)
