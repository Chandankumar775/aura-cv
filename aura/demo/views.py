"""Hard-coded, illustrative module views (tables and chart series) for the demo UI.

Values are consistent with the demo findings in ``scenario.py`` but are not measured.
"""

from __future__ import annotations

import math
import random

from aura.demo.catalog import BATTERY, CLASSES, CONTRIBUTORS
from aura.demo.scenario import ids


def _confusion(n: int, rng: random.Random, relabel: tuple[int, int, float] | None = None, noise: float = 0.02) -> list[list[int]]:
    per = n // len(CLASSES)
    m = [[0] * len(CLASSES) for _ in CLASSES]
    for i in range(len(CLASSES)):
        off = [int(per * noise * rng.random()) for _ in CLASSES]
        off[i] = 0
        if relabel and relabel[0] == i:
            off[relabel[1]] = int(per * relabel[2])
        m[i] = off
        m[i][i] = per - sum(off)
    return m


def data_view(dataset_id: str) -> dict:
    rng = random.Random(dataset_id)
    if dataset_id == "ds_vehicles_v3":
        rows = [
            ("contributor_C", 962, 108, 97.8, (93.1, 99.4), {"trigger": 41, "flip": 0, "systematic": 67, "duplicate": 0, "ood": 0}, "QUARANTINE"),
            ("contributor_D", 1004, 93, 41.2, (28.7, 55.0), {"trigger": 0, "flip": 0, "systematic": 0, "duplicate": 93, "ood": 0}, "REVIEW"),
            ("contributor_E", 921, 23, 22.0, (11.4, 36.2), {"trigger": 0, "flip": 23, "systematic": 0, "duplicate": 0, "ood": 0}, "ACCEPT"),
            ("contributor_B", 978, 14, 12.6, (5.1, 24.8), {"trigger": 0, "flip": 0, "systematic": 0, "duplicate": 0, "ood": 14}, "ACCEPT"),
            ("contributor_A", 955, 3, 1.9, (0.3, 7.7), {"trigger": 0, "flip": 2, "systematic": 0, "duplicate": 0, "ood": 1}, "ACCEPT"),
        ]
        confusion = {
            cid: _confusion(n, random.Random(cid), (0, 3, 0.184) if cid == "contributor_C" else None, 0.05 if cid == "contributor_E" else 0.012)
            for cid, n, *_ in rows
        }
        confusion["pooled_others"] = _confusion(3858, random.Random("pooled"), (0, 3, 0.011), 0.012)
        return {
            "has_metadata": True,
            "classes": CLASSES,
            "totals": {"images": 4820, "flagged": 241, "contributors": 5, "batches": 14},
            "source_risk": [
                {"contributor_id": cid, "name": CONTRIBUTORS[cid]["name"], "samples": n, "flagged": f, "risk": r, "ci": list(ci), "breakdown": b, "disposition": d}
                for cid, n, f, r, ci, b, d in rows
            ],
            "counts_by_attack": {"trigger": 41, "flip": 25, "systematic": 67, "duplicate": 93, "ood": 15, "annotation": 3},
            "triggers": {
                "location": {"x": 202, "y": 202, "w": 14, "h": 14, "image_size": 224, "label": "bottom-right 14×14"},
                "label_concentration": {"civilian_car": 39, "truck": 2},
                "samples": ids("C", "trg", 3, 12),
                "residual_samples": ids("C", "trg", 3, 6, 13),
            },
            "label_issues": [
                {"sample_id": f"E-flp-{i % 5}-{i:04d}", "contributor": "contributor_E", "given": CLASSES[(i + 2) % 5], "consensus": CLASSES[i % 5], "agreement": round(0.9 + rng.random() * 0.1, 2),
                 "neighbours": [f"A-ok-{i % 5}-{j:04d}" for j in range(i * 3, i * 3 + 4)]}
                for i in range(1, 9)
            ],
            "systematic": {"contributor": "contributor_C", "source_class": "truck", "target_class": "civilian_car", "rate": 0.184, "pooled_rate": 0.011, "samples": ids("C", "sys", 0, 8)},
            "duplicate_clusters": [
                {"cluster_id": "dup-01", "size": 64, "contributor": "contributor_D", "min_similarity": 0.968, "method": "phash+embed", "members": ids("D", "dup", 1, 8)},
                {"cluster_id": "dup-02", "size": 18, "contributor": "contributor_D", "min_similarity": 0.972, "method": "embed", "members": ids("D", "dup", 2, 6)},
                {"cluster_id": "dup-03", "size": 11, "contributor": "contributor_D", "min_similarity": 0.975, "method": "embed", "members": ids("D", "dup", 4, 6)},
            ],
            "ood": [
                {"sample_id": s, "contributor": "contributor_B", "score": round(3.1 + rng.random() * 1.8, 2), "threshold": 1.0, "nearest": [f"A-ok-2-{k:04d}" for k in range(n * 2, n * 2 + 3)]}
                for n, s in enumerate(ids("B", "ood", 2, 6))
            ],
            "confusion": confusion,
        }
    if dataset_id == "ds_vehicles_v2":
        rows = [("contributor_A", 1560, 3, 2.1, (0.4, 8.1)), ("contributor_E", 1540, 3, 2.3, (0.5, 8.4))]
        return {
            "has_metadata": True,
            "classes": CLASSES,
            "totals": {"images": 3100, "flagged": 6, "contributors": 2, "batches": 6},
            "source_risk": [
                {"contributor_id": cid, "name": CONTRIBUTORS[cid]["name"], "samples": n, "flagged": f, "risk": r, "ci": list(ci),
                 "breakdown": {"trigger": 0, "flip": 2, "systematic": 0, "duplicate": 1, "ood": 0}, "disposition": "ACCEPT"}
                for cid, n, f, r, ci in rows
            ],
            "counts_by_attack": {"trigger": 0, "flip": 4, "systematic": 0, "duplicate": 4, "ood": 0, "annotation": 0},
            "triggers": None, "label_issues": [], "systematic": None, "duplicate_clusters": [], "ood": [],
            "confusion": {cid: _confusion(n, random.Random(cid)) for cid, n, *_ in rows},
        }
    return {
        "has_metadata": False,
        "classes": CLASSES,
        "totals": {"images": 1260, "flagged": 3, "contributors": 0, "batches": 0},
        "source_risk": [],
        "counts_by_attack": {"trigger": 0, "flip": 0, "systematic": 0, "duplicate": 0, "ood": 3, "annotation": 0},
        "triggers": None, "label_issues": [], "systematic": None, "duplicate_clusters": [],
        "ood": [{"sample_id": s, "contributor": None, "score": 2.4, "threshold": 1.0, "nearest": []} for s in ids("X", "ood", 1, 3)],
        "confusion": {},
    }


def model_view(model: dict, access: str) -> dict:
    mid = model["id"]
    wb = access == "WB"
    backdoored = mid in ("mdl_vehnet_v21", "mdl_vehnet_v21_onnx")
    view = {
        "access_level": access,
        "detected_access_level": model["detected_access_level"],
        "access_banner": {
            "WB": "Assessed with WHITE-BOX access (weights, activations and gradients).",
            "BB-S": "Assessed with BLACK-BOX access (output scores only). White-box checks are unavailable; fallbacks were used.",
            "BB-L": "Assessed with BLACK-BOX access (labels only). Score- and white-box checks are unavailable.",
        }[access],
        "identity": {
            "weight_digest": model["weight_digest"],
            "registered_digest": model["registered_digest"],
            "digest_match": model["weight_digest"] == model["registered_digest"],
            "structure_match": (None if not wb else mid != "mdl_vehnet_v22"),
            "fingerprint_agreement": 0.831 if mid == "mdl_vehnet_v22" else 0.996,
            "measured_accuracy": 0.95 if mid == "mdl_vehnet_v22" else 0.912,
            "claimed_accuracy": model.get("claimed_accuracy"),
        },
        "battery": {"version": BATTERY["version"], "digest": BATTERY["digest"], "images": 300},
        "triggers": (
            [{"class": c, "class_index": i, "anomaly_index": a, "anomalous": a > 2.0, "mask_l1": m}
             for i, (c, a, m) in enumerate([("truck", 0.41, 231.0), ("apc", 0.88, 198.4), ("tank", 0.23, 244.9), ("civilian_car", 4.62 if backdoored else 1.12, 38.0 if backdoored else 187.0), ("pickup", 1.07, 176.3)])]
            if wb else None
        ),
        "strip": None if mid == "mdl_vehnet_v22" or access == "BB-L" else {
            "histogram": [{"bin": round(b * 0.1, 1), "clean": cl, "patched": pa} for b, cl, pa in [(0, 1, 38), (1, 2, 17), (2, 3, 7), (3, 6, 5), (4, 11, 4), (5, 17, 3), (6, 22, 2), (7, 19, 2), (8, 12, 1), (9, 7, 1)]],
            "threshold": 0.2,
        },
        "patch_probe": None if mid == "mdl_vehnet_v22" else [
            {"patch": "M1 candidate (contributor C)", "flip_rate": 0.714, "target": "civilian_car"},
            {"patch": "checkerboard 16px", "flip_rate": 0.021, "target": "-"},
            {"patch": "solid white 16px", "flip_rate": 0.012, "target": "-"},
            {"patch": "random noise 16px", "flip_rate": 0.018, "target": "-"},
        ],
        "confidence": {"WB": 0.88, "BB-S": 0.71, "BB-L": 0.55}[access],
        "limitations": [
            "Backdoor search covers patch-like triggers; sample-specific or invisible dynamic triggers are not supported.",
            "Reference battery is drawn from the declared reference; a trigger that only activates on other terrain would be missed.",
        ] + ([] if wb else ["White-box checks (structure, trigger reconstruction, activations, weights) could not run at this access level."]),
    }
    return view


def _gauss(rng: random.Random, n: int, cx: float, cy: float, sx: float, sy: float) -> list[list[float]]:
    return [[round(rng.gauss(cx, sx), 3), round(rng.gauss(cy, sy), 3)] for _ in range(n)]


def shift_view(batch_id: str) -> dict:
    rng = random.Random(batch_id)
    bands = ["0–0.05", "0.05–0.1", "0.1–0.2", "0.2–0.3", "0.3–0.4", "0.4–0.5"]
    ref_fft = [1.0, 0.62, 0.34, 0.17, 0.08, 0.04]
    ref_points = _gauss(random.Random("ref"), 160, 0, 0, 1.0, 0.8)
    if batch_id == "ib_sector7_dawn":
        descriptors = [
            ("Mean luminance", "illumination", -1.9), ("Dynamic range", "illumination", -1.1), ("Contrast", "illumination", -1.4),
            ("Colour temperature", "season", 0.9), ("Green-channel share", "season", -0.6), ("Sharpness (Laplacian var.)", "sensor", -1.2),
            ("Noise estimate", "sensor", 0.4), ("High-freq. band energy", "acquisition", -0.8), ("Edge density", "terrain", -0.3),
            ("JPEG quality", "acquisition", -0.1),
        ]
        obs_fft = [1.0, 0.55, 0.26, 0.11, 0.045, 0.02]
        obs_points = _gauss(rng, 140, 1.7, -0.6, 1.1, 0.9)
        rules = [
            {"rule": "Shift is broad: 92% of images move coherently", "supports": "PROBABLE_OPERATIONAL_DRIFT", "fired": True},
            {"rule": "Global luminance drop with high-frequency loss (haze / low light)", "supports": "PROBABLE_OPERATIONAL_DRIFT", "fired": True},
            {"rule": "Consistent with supplied metadata (dawn, light haze)", "supports": "PROBABLE_OPERATIONAL_DRIFT", "fired": True},
            {"rule": "Gradual confidence degradation, no one-class flips", "supports": "PROBABLE_OPERATIONAL_DRIFT", "fired": True},
            {"rule": "Localised / subset-concentrated shift", "supports": "SUSPICIOUS_MANIPULATION", "fired": False},
            {"rule": "Structured high-frequency energy above reference noise", "supports": "SUSPICIOUS_MANIPULATION", "fired": False},
            {"rule": "Sharp prediction flips toward one class", "supports": "SUSPICIOUS_MANIPULATION", "fired": False},
            {"rule": "Known ambiguity: low-light sensor noise", "supports": "INCONCLUSIVE", "fired": False},
        ]
        return {
            "shift_detected": True,
            "verdict": "PROBABLE_OPERATIONAL_DRIFT",
            "verdict_confidence": 0.78,
            "calibrated_risk": 0.64,
            "calibration": {"method": "isotonic", "ece": 0.041, "extrapolated": False, "reliability": [[0.1, 0.08], [0.3, 0.27], [0.5, 0.53], [0.7, 0.68], [0.9, 0.87]]},
            "tests": {"mmd2": 0.084, "p_value": 0.001, "permutations": 1000, "novel_fraction": 0.31},
            "characterisation": "The dawn-patrol batch is darker and lower-contrast than the summer-daylight reference, with softer detail and a cooler colour cast. The pattern is typical of low sun and light haze and matches the supplied acquisition metadata. Terrain descriptors are close to the reference.",
            "factors": {"illumination": -1.9, "season": 0.9, "sensor": -1.2, "acquisition": -0.8, "terrain": -0.3},
            "descriptors": [{"name": n, "factor": f, "effect_size": d} for n, f, d in descriptors],
            "spectrum": [{"band": b, "reference": r, "observed": o} for b, r, o in zip(bands, ref_fft, obs_fft)],
            "projection": {"reference": ref_points, "observed": obs_points},
            "rules": rules,
            "novel_samples": [f"S-s7-{i % 5}-{i:04d}" for i in range(1, 9)],
            "metadata": {"time_of_day": "05:40-06:25", "sensor": "EO-2 gimbal", "weather": "light haze"},
        }
    descriptors = [
        ("Mean luminance", "illumination", 0.08), ("Dynamic range", "illumination", 0.1), ("Contrast", "illumination", 0.15),
        ("Colour temperature", "season", -0.05), ("Green-channel share", "season", 0.02), ("Sharpness (Laplacian var.)", "sensor", 0.4),
        ("Noise estimate", "sensor", 1.1), ("High-freq. band energy", "acquisition", 2.7), ("Edge density", "terrain", 0.6),
        ("JPEG quality", "acquisition", 0.0),
    ]
    obs_points = _gauss(rng, 180, 0.1, 0.05, 1.0, 0.8) + _gauss(rng, 30, 3.2, 2.4, 0.35, 0.3)
    return {
        "shift_detected": True,
        "verdict": "SUSPICIOUS_MANIPULATION",
        "verdict_confidence": 0.74,
        "calibrated_risk": 0.81,
        "calibration": {"method": "isotonic", "ece": 0.041, "extrapolated": False, "reliability": [[0.1, 0.08], [0.3, 0.27], [0.5, 0.53], [0.7, 0.68], [0.9, 0.87]]},
        "tests": {"mmd2": 0.031, "p_value": 0.002, "permutations": 1000, "novel_fraction": 0.14},
        "characterisation": "Overall brightness, colour and sharpness match the reference. The difference is concentrated in about 14% of images, which carry structured high-frequency energy well above the reference sensor-noise profile and flip sharply to 'civilian_car'. This pattern is not explained by weather, season or sensor change.",
        "factors": {"illumination": 0.15, "season": -0.05, "sensor": 1.1, "acquisition": 2.7, "terrain": 0.6},
        "descriptors": [{"name": n, "factor": f, "effect_size": d} for n, f, d in descriptors],
        "spectrum": [{"band": b, "reference": r, "observed": o} for b, r, o in zip(bands, ref_fft, [1.0, 0.63, 0.36, 0.24, 0.19, 0.16])],
        "projection": {"reference": ref_points, "observed": obs_points},
        "rules": [
            {"rule": "Localised / subset-concentrated shift (14% of images)", "supports": "SUSPICIOUS_MANIPULATION", "fired": True},
            {"rule": "Structured high-frequency energy above reference noise", "supports": "SUSPICIOUS_MANIPULATION", "fired": True},
            {"rule": "Sharp prediction flips toward one class", "supports": "SUSPICIOUS_MANIPULATION", "fired": True},
            {"rule": "Small pixel change, large output change", "supports": "SUSPICIOUS_MANIPULATION", "fired": True},
            {"rule": "Shift is broad and coherent", "supports": "PROBABLE_OPERATIONAL_DRIFT", "fired": False},
            {"rule": "Physically plausible descriptor pattern", "supports": "PROBABLE_OPERATIONAL_DRIFT", "fired": False},
            {"rule": "Known ambiguity: low-light sensor noise", "supports": "INCONCLUSIVE", "fired": True},
        ],
        "novel_samples": [f"S-s9-{i % 5}-{i:04d}" for i in range(1, 9)],
        "metadata": {},
    }


def spark(seed: str, n: int = 12, base: float = 0.5, amp: float = 0.3) -> list[float]:
    rng = random.Random(seed)
    return [round(base + amp * math.sin(i / 2 + rng.random()), 3) for i in range(n)]
