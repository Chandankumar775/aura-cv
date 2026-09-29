"""Coverage statement: single source of truth (CLAUDE.md A16; R-GOV-3, R-DEL-5).

Embedded in every report and served to the UI at ``/api/v1/coverage``.
"""

from __future__ import annotations

COVERAGE: dict[str, list[str]] = {
    "supported": [
        "Visible patch and blended triggers in a subset of samples",
        "Random label flipping",
        "Systematic class-to-class mislabelling by a contributor",
        "Near-duplicate flooding via common augmentations",
        "Out-of-distribution insertion",
        "Annotation errors",
        "Contributor / batch / source risk when metadata is supplied",
        "Weight-file substitution vs registered digest",
        "Behavioural change vs registered fingerprint",
        "Patch-like backdoors in classification models (white-box reconstruction, black-box probing)",
        "Inference-record alteration, forgery, substitution, replay, deletion and reordering",
        "Model / configuration substitution and input mismatch in inference records",
        "Global illumination, contrast, colour, sharpness, noise, resolution and compression shifts, and domain change",
        "Audit-log edit, deletion and truncation (truncation relative to an exported head hash)",
    ],
    "partial": [
        "Backdoors in detection models (digest, fingerprint and probing only)",
        "Trigger detection without the contributed model's activations",
        "Drift vs manipulation - decisive only when evidence rules agree",
        "Gradient-based checks on ONNX models",
        "Terrain / season characterisation without acquisition metadata",
    ],
    "unsupported": [
        "Clean-label poisoning",
        "Sample-specific, input-aware or invisible dynamic triggers",
        "Physical-world triggers and adversarial patches on real objects",
        "Adaptive attackers who optimise against AURA-CV",
        "Poisoning spread evenly across all contributors",
        "Compromised signing keys or signing host",
        "Input forgery before signing",
        "Privacy attacks and model extraction",
        "Non-RGB modalities (SAR, thermal, multispectral) and video temporal attacks",
    ],
    "assumptions": [
        "AURA-CV code, bundled weights and reference battery are trusted",
        "The declared reference and trusted reference set are clean and representative",
        "Keys are generated and held in the trusted environment",
        "At least some contributors are honest, so sources can be compared",
        "The model's declared interface is correct",
    ],
    "known_limitations": [
        "Thresholds tuned on generated scenarios may need recalibration for new domains",
        "Spectral evidence can confuse low-light noise with manipulation, and low-frequency adversarial perturbations with drift",
        "Weight statistics are weak signals",
        "Small contributors get wide uncertainty intervals",
        "Performance is measured only on the stated hardware",
    ],
}
