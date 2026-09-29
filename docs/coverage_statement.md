# Coverage Statement (draft)

> **DRAFT, placeholder location.** From Milestone M7 the single source of truth is
> `aura/m5_governance/coverage.py`, and this file is generated from it and embedded in
> every report (R-GOV-3, R-DEL-5). Until then, the content below is copied from
> CLAUDE.md A16. It states **intended** coverage; nothing below has been measured yet.

## Supported
Visible patch and blended triggers in a subset of samples; random label flipping;
systematic class-to-class mislabelling by a contributor; near-duplicate flooding via
common augmentations; OOD insertion; annotation errors; contributor/batch/source risk
when metadata is supplied; weight-file substitution vs registered digest; behavioural
change vs registered fingerprint; patch-like backdoors in classification models (WB
reconstruction, BB probing); record alteration, forgery, substitution, replay, deletion,
reordering, model/config substitution, input mismatch; global illumination, contrast,
colour, sharpness, noise, resolution and compression shifts and domain change; audit log
edit, deletion, and truncation (relative to an exported head hash).

## Partial
Backdoors in detection models (digest, fingerprint and probing only); trigger detection
without the contributed model's activations; drift vs manipulation (decisive only when
evidence rules agree); gradient-based checks on ONNX; terrain/season characterisation
without metadata.

## Not supported
Clean-label poisoning; sample-specific/input-aware/invisible dynamic triggers;
physical-world triggers and adversarial patches on real objects; adaptive attackers
targeting AURA-CV; poisoning spread evenly across all contributors; compromised signing
keys or signing host; input forgery before signing; privacy attacks and model
extraction; non-RGB modalities (SAR, thermal, multispectral) and video temporal attacks.

## Assumptions
AURA-CV code, bundled weights and battery are trusted; declared reference and trusted
reference set are clean and representative; keys are generated and held in the trusted
environment; at least some contributors are honest for source comparison; the model's
declared interface is correct.

## Known limitations
Thresholds tuned on generated scenarios may need recalibration for new domains; FFT
evidence can confuse low-light noise with manipulation and low-frequency adversarial
perturbations with drift; weight statistics are weak signals; small contributors get
wide uncertainty; performance measured only on stated hardware.
