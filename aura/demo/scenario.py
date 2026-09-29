"""Demo Check plugins with hard-coded, illustrative outputs.

These are genuine ``Check`` plugins run by the genuine ``Scheduler`` (so access gating,
UNAVAILABLE findings, fallbacks, policy dispositions, schema validation and audit
events are all real). What is hard-coded is the *detector output*: each check returns
pre-written findings for the demo assets, standing in for the real detectors that
milestones M4-M6 implement. Inference-record findings are the exception: they come
from actually verifying the signed demo stream.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aura.core.checks import AssessmentContext, BaseCheck, CheckRegistry
from aura.core.policy import HardOverride
from aura.core.types import AccessLevel, AssetRef, AssetType, Finding, ModuleId, Severity

HIGH, MED, LOW, CRIT = Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.CRITICAL


def ids(who: str, kind: str, cls: int, n: int, start: int = 1) -> list[str]:
    return [f"{who}-{kind}-{cls}-{i:04d}" for i in range(start, start + n)]


def contributor(cid: str) -> AssetRef:
    return AssetRef(type=AssetType.CONTRIBUTOR, id=cid)


class DemoCheck(BaseCheck):
    def __init__(
        self,
        check_id: str,
        module: ModuleId,
        fn: Callable[["DemoCheck", AssessmentContext], list[Finding]],
        access: AccessLevel = AccessLevel.NONE,
        inputs: tuple[str, ...] = (),
        fallback: str | None = None,
        applicable: Callable[[AssessmentContext], tuple[bool, str]] | None = None,
        params: dict[str, Any] | None = None,
        asset_input: str | None = None,
    ):
        self.id, self.module, self.fn = check_id, module, fn
        self.requires_access, self.requires_inputs = access, set(inputs)
        self.fallback_check_id, self._applicable = fallback, applicable
        self._params, self.asset_input = params or {}, asset_input

    def is_applicable(self, ctx: AssessmentContext) -> tuple[bool, str]:
        return self._applicable(ctx) if self._applicable else (True, "")

    def parameters(self, ctx: AssessmentContext) -> dict[str, Any]:
        return dict(self._params)

    def run(self, ctx: AssessmentContext, progress) -> list[Finding]:
        return self.fn(self, ctx)

    def flag(self, ctx: AssessmentContext, reason: str, severity: Severity, confidence: float, asset: AssetRef, *,
             metrics: dict | None = None, samples: list[str] | None = None, limitations: list[str] | None = None,
             overrides: list[HardOverride] | None = None, **extra: Any) -> Finding:
        return ctx.make_finding(
            module=self.module, check_id=self.id, reason=reason, severity=severity, confidence=confidence,
            affected_asset=asset,
            evidence={"metrics": metrics or {}, "thresholds": self.parameters(ctx), "sample_ids": samples or [], **extra},
            limitations=limitations or [], overrides=overrides or [],
        )


def _ds(ctx: AssessmentContext) -> str:
    return ctx.inputs["dataset"]["id"]


def _mdl(ctx: AssessmentContext) -> str:
    return ctx.inputs["model"]["id"]


def _batch(ctx: AssessmentContext) -> str:
    return ctx.inputs["input_batch"]["id"]


def _dsref(ctx: AssessmentContext) -> AssetRef:
    return ctx.assets["dataset"]


# ============================================================== Module 1: data

def m1_sanity(c: DemoCheck, ctx):
    if _ds(ctx) != "ds_vehicles_v3":
        return []
    return [c.flag(ctx, "Three files in the dataset cannot be used as supplied: one image is unreadable, one annotation uses an undefined class id, and one bounding box has zero area.",
                   LOW, 0.99, _dsref(ctx), metrics={"unreadable_files": 1, "invalid_class_ids": 1, "zero_area_boxes": 1},
                   samples=["B-ok-0-0913", "D-ok-2-1177", "E-ok-4-0288"])]


def m1_patch(c, ctx):
    if _ds(ctx) != "ds_vehicles_v3":
        return []
    return [c.flag(ctx, "Allied Source Delta (contributor C) supplied 41 images that share an identical 14×14 px patch in the bottom-right corner; 39 of them are labelled 'civilian_car', far above that contributor's normal share of the class.",
                   CRIT, 0.93, contributor("contributor_C"),
                   metrics={"images_with_patch": 41, "fraction_in_target_class": 0.951, "contributor_share_of_class_baseline": 0.18, "patch_location": "bottom-right", "patch_size_px": 14},
                   samples=ids("C", "trg", 3, 39) + ids("C", "trg", 0, 2, 40),
                   limitations=["Pixel-level patch search: blended or invisible triggers would not be found by this check."],
                   overlay={"x": 202, "y": 202, "w": 14, "h": 14, "image_size": 224})]


def m1_hf(c, ctx):
    if _ds(ctx) != "ds_vehicles_v3":
        return []
    return [c.flag(ctx, "A consistent high-frequency residue appears in the same bottom-right region of 38 images from contributor C, matching the repeated-patch finding.",
                   HIGH, 0.71, contributor("contributor_C"), metrics={"images_with_residue": 38, "residue_energy_z": 5.4, "region": "bottom-right 24×24"},
                   samples=ids("C", "trg", 3, 38), limitations=["Supporting evidence; natural textures can create residue in small numbers of images."])]


def m1_cluster(c, ctx):
    if _ds(ctx) != "ds_vehicles_v3":
        return []
    return [c.flag(ctx, "Inside class 'civilian_car', 44 of 912 images form a small, well-separated cluster in feature space; 39 of the 44 come from contributor C and carry the corner patch.",
                   HIGH, 0.84, _dsref(ctx), metrics={"class": "civilian_car", "cluster_size": 44, "class_size": 912, "silhouette": 0.61, "from_contributor_C": 39},
                   samples=ids("C", "trg", 3, 30), limitations=["Uses the frozen backbone, not the contributed model's activations (Partial coverage)."])]


def m1_spectral(c, ctx):
    if _ds(ctx) != "ds_vehicles_v3":
        return []
    return [c.flag(ctx, "Spectral-signature scoring puts 36 of the 41 patched images among the top 1.5% outliers of class 'civilian_car'.",
                   MED, 0.68, _dsref(ctx), metrics={"class": "civilian_car", "outliers_flagged": 14, "overlap_with_patch_set": 36, "percentile": 98.5},
                   samples=ids("C", "trg", 3, 14))]


def m1_knn(c, ctx):
    ds = _ds(ctx)
    if ds == "ds_vehicles_v3":
        return [c.flag(ctx, "Field Unit West (contributor E) has 23 images whose label disagrees with 9 or more of their 10 nearest neighbours, spread across all classes - consistent with random label flipping.",
                       MED, 0.66, contributor("contributor_E"), metrics={"flagged_samples": 23, "mean_neighbour_agreement": 0.07, "classes_affected": 5},
                       samples=[f"E-flp-{i % 5}-{i:04d}" for i in range(1, 24)])]
    if ds == "ds_vehicles_v2":
        return [c.flag(ctx, "Four images have labels that disagree with most of their nearest neighbours; the pattern is isolated and consistent with ordinary annotation noise.",
                       LOW, 0.41, _dsref(ctx), metrics={"flagged_samples": 4}, samples=[f"A-flp-{i}-{i:04d}" for i in range(1, 5)])]
    return []


def m1_confident(c, ctx):
    if _ds(ctx) != "ds_vehicles_v3":
        return []
    return [c.flag(ctx, "A cross-validated classifier confidently predicts a different class for 31 images (probability ≥ 0.90); 19 of them overlap with the neighbour-consensus flags.",
                   MED, 0.58, _dsref(ctx), metrics={"flagged_samples": 31, "overlap_with_knn": 19, "min_out_of_sample_prob": 0.9},
                   samples=[f"E-flp-{i % 5}-{i:04d}" for i in range(1, 20)])]


def m1_systematic(c, ctx):
    if _ds(ctx) != "ds_vehicles_v3":
        return []
    return [c.flag(ctx, "Contributor C labels 18.4% of images that look like 'truck' as 'civilian_car', against 1.1% for all other contributors combined - a systematic relabelling, not random noise.",
                   HIGH, 0.88, contributor("contributor_C"),
                   metrics={"source_class": "truck", "target_class": "civilian_car", "contributor_rate": 0.184, "pooled_rate": 0.011, "samples": 67, "holm_adjusted_p": 3.2e-11},
                   samples=ids("C", "sys", 0, 24))]


def m1_phash(c, ctx):
    if _ds(ctx) != "ds_vehicles_v3":
        return []
    return [c.flag(ctx, "Vendor Arcadia Labs (contributor D) supplied 64 near-identical copies of a single image (flips, brightness and JPEG changes), inflating one scene's weight in training.",
                   MED, 0.91, contributor("contributor_D"), metrics={"cluster_size": 64, "max_hamming": 5, "augmentations_seen": ["h-flip", "brightness", "jpeg"]},
                   samples=ids("D", "dup", 1, 16), clusters=[{"cluster_id": "dup-01", "size": 64}])]


def m1_embed(c, ctx):
    ds = _ds(ctx)
    if ds == "ds_vehicles_v3":
        return [c.flag(ctx, "Embedding similarity finds two further near-duplicate groups from contributor D (18 and 11 images) that the perceptual hash missed.",
                       LOW, 0.77, contributor("contributor_D"), metrics={"extra_clusters": 2, "sizes": [18, 11], "min_cosine": 0.972},
                       samples=ids("D", "dup", 2, 8))]
    if ds == "ds_vehicles_v2":
        return [c.flag(ctx, "Two pairs of images are near-duplicates, most likely consecutive video frames; no flooding pattern.",
                       LOW, 0.52, _dsref(ctx), metrics={"pairs": 2, "min_cosine": 0.981}, samples=ids("A", "dup", 4, 4))]
    return []


def m1_ood_knn(c, ctx):
    ds = _ds(ctx)
    if ds == "ds_vehicles_v3":
        return [c.flag(ctx, "Vendor Kestrel Imaging (contributor B) supplied 12 images that lie beyond the 99th percentile of distance from the reference distribution; they show structured indoor scenes, not aerial terrain.",
                       MED, 0.72, contributor("contributor_B"), metrics={"flagged_samples": 12, "threshold_percentile": 99, "median_score_ratio": 3.4},
                       samples=ids("B", "ood", 2, 12))]
    if ds == "ds_vehicles_nometa":
        return [c.flag(ctx, "Three images are far from the reference distribution and may not belong in this dataset.",
                       LOW, 0.61, _dsref(ctx), metrics={"flagged_samples": 3}, samples=ids("X", "ood", 1, 3))]
    return []


def m1_ood_maha(c, ctx):
    if _ds(ctx) != "ds_vehicles_v3":
        return []
    return [c.flag(ctx, "Class-conditional scoring confirms 9 of contributor B's 12 out-of-distribution images and adds 2 borderline images.",
                   LOW, 0.55, contributor("contributor_B"), metrics={"confirmed": 9, "additional": 2}, samples=ids("B", "ood", 2, 9))]


def m1_source(c, ctx):
    if _ds(ctx) != "ds_vehicles_v3":
        return []
    out = [
        c.flag(ctx, "Allied Source Delta (contributor C) carries the highest source risk: 108 of its 962 images are implicated in trigger injection and systematic relabelling. Risk 97.8 / 100.",
               CRIT, 0.95, contributor("contributor_C"), metrics={"risk_score": 97.8, "samples": 962, "weighted_flags": 104.6, "posterior_mean": 0.109, "p0": 0.02, "breakdown": {"trigger": 41, "systematic": 67, "flip": 0, "duplicate": 0, "ood": 0}}),
        c.flag(ctx, "Vendor Arcadia Labs (contributor D) is elevated because of duplicate flooding (93 near-copies). Risk 41.2 / 100.",
               MED, 0.62, contributor("contributor_D"), metrics={"risk_score": 41.2, "samples": 1004, "breakdown": {"duplicate": 93}}),
        c.flag(ctx, "Field Unit West (contributor E) shows a modest rate of random label errors. Risk 22.0 / 100.",
               LOW, 0.45, contributor("contributor_E"), metrics={"risk_score": 22.0, "samples": 921, "breakdown": {"flip": 23}}),
    ]
    return out


def _has_meta(ctx):
    if ctx.inputs["dataset"].get("has_contributor_metadata"):
        return True, ""
    return False, "no contributor/batch/source metadata supplied"


# ============================================================= Module 2: model

def m2_digest(c, ctx):
    m = ctx.inputs["model"]
    if m["weight_digest"] == m["registered_digest"]:
        return []
    return [c.flag(ctx, "The weight file does not match the digest registered for this model: the supplied model has been substituted or modified since registration.",
                   CRIT, 0.99, ctx.assets["model"], metrics={"weight_digest": m["weight_digest"], "registered_digest": m["registered_digest"]},
                   overrides=[HardOverride.MODEL_DIGEST_MISMATCH])]


def m2_structure(c, ctx):
    if _mdl(ctx) != "mdl_vehnet_v22":
        return []
    return [c.flag(ctx, "The layer graph differs from the registered architecture: two additional layers appear before the classifier head.",
                   HIGH, 0.95, ctx.assets["model"], metrics={"registered_layers": 62, "observed_layers": 64, "changed_blocks": ["fc.pre_1", "fc.pre_2"]})]


def m2_fingerprint(c, ctx):
    if _mdl(ctx) != "mdl_vehnet_v22":
        return []
    return [c.flag(ctx, "On the reference battery the model agrees with the registered fingerprint on only 83.1% of images (expected ≥ 98%): its behaviour has materially changed.",
                   HIGH, 0.86, ctx.assets["model"], metrics={"top1_agreement": 0.831, "expected_min": 0.98, "js_divergence": 0.142})]


def m2_refacc(c, ctx):
    if _mdl(ctx) == "mdl_vehnet_v22":
        return []
    return [c.flag(ctx, "Clean accuracy on the reference battery is 91.2%, below the supplier's claimed 94.0%; the gap is small and within what a domain difference could explain.",
                   LOW, 0.60, ctx.assets["model"], metrics={"measured_accuracy": 0.912, "claimed_accuracy": 0.94, "battery_images": 300})]


def m2_recon(c, ctx):
    if _mdl(ctx) != "mdl_vehnet_v21":
        return []
    return [c.flag(ctx, "Trigger reconstruction finds an unusually small trigger that turns almost any image into 'civilian_car' (anomaly index 4.62; values above 2.0 indicate a backdoor). The trigger sits in the bottom-right corner, matching contributor C's patch.",
                   CRIT, 0.90, ctx.assets["model"],
                   metrics={"target_class": "civilian_car", "anomaly_index": 4.62, "mask_l1": 38.0, "median_mask_l1": 212.5, "attack_success_rate": 0.97},
                   limitations=["Optimisation budget: 400 iterations per class; very large or distributed triggers may not be recovered."],
                   triggers=[{"class": k, "anomaly_index": v} for k, v in [("truck", 0.41), ("apc", 0.88), ("tank", 0.23), ("civilian_car", 4.62), ("pickup", 1.07)]])]


def m2_activation(c, ctx):
    if _mdl(ctx) != "mdl_vehnet_v21":
        return []
    return [c.flag(ctx, "Three neurons in layer4.1 stay silent on clean images but fire strongly when the reconstructed trigger is present - a typical backdoor pathway.",
                   HIGH, 0.74, ctx.assets["model"], metrics={"layer": "layer4.1", "neurons": [117, 342, 409], "clean_mean_activation": 0.004, "trigger_mean_activation": 0.187})]


def m2_params(c, ctx):
    if _mdl(ctx) != "mdl_vehnet_v21":
        return []
    return [c.flag(ctx, "Weight kurtosis in layer4.1.conv2 is unusually high compared with the reference architecture. This is weak, supporting evidence only.",
                   MED, 0.45, ctx.assets["model"], metrics={"layer": "layer4.1.conv2", "kurtosis_z": 3.1},
                   limitations=["Weight statistics are weak signals; severity is capped at MEDIUM."])]


def m2_strip(c, ctx):
    if _mdl(ctx) == "mdl_vehnet_v22":
        return []
    return [c.flag(ctx, "When clean images are superimposed on patched inputs, 62% keep predicting 'civilian_car' with near-zero entropy, versus 3% for clean inputs - the patch dominates the model's decision.",
                   HIGH, 0.82, ctx.assets["model"], metrics={"low_entropy_rate_patched": 0.62, "low_entropy_rate_clean": 0.03, "entropy_threshold": 0.2},
                   histogram=[{"bin": round(b * 0.1, 1), "clean": cl, "patched": pa} for b, cl, pa in [(0, 1, 38), (1, 2, 17), (2, 3, 7), (3, 6, 5), (4, 11, 4), (5, 17, 3), (6, 22, 2), (7, 19, 2), (8, 12, 1), (9, 7, 1)]])]


def m2_probe(c, ctx):
    if _mdl(ctx) == "mdl_vehnet_v22":
        return []
    return [c.flag(ctx, "Pasting contributor C's corner patch onto clean battery images flips 71.4% of them to 'civilian_car'; random control patches flip fewer than 2%.",
                   HIGH, 0.93, ctx.assets["model"], metrics={"flip_rate_candidate_patch": 0.714, "flip_rate_random_patches": 0.018, "target_class": "civilian_car", "probe_images": 300},
                   probes=[{"patch": "M1 candidate (contributor C)", "flip_rate": 0.714, "target": "civilian_car"},
                           {"patch": "checkerboard 16px", "flip_rate": 0.021, "target": "-"},
                           {"patch": "solid white 16px", "flip_rate": 0.012, "target": "-"},
                           {"patch": "random noise 16px", "flip_rate": 0.018, "target": "-"}])]


def _classification_only(ctx):
    if ctx.inputs["model"].get("task") == "detection":
        return False, "not supported for detection models in this version"
    if ctx.inputs["model"].get("format") != "torchscript":
        return False, "gradients are only available for TorchScript models"
    return True, ""


# ========================================================= Module 3: provenance

def m3_verify(c, ctx):
    findings = []
    for r in ctx.inputs["records"]["verification"]:
        if r["status"] == "VERIFIED":
            continue
        rec = r["record"]
        failed = [s for s in r["steps"] if s["passed"] is False]
        overrides = []
        if r["status"] in ("ALTERED", "UNVERIFIABLE", "SUBSTITUTED"):
            overrides.append(HardOverride.SIGNATURE_FAILURE)
        if r["status"] == "MODEL_MISMATCH":
            overrides.append(HardOverride.MODEL_DIGEST_MISMATCH)
        sev = CRIT if r["status"] in ("ALTERED", "UNVERIFIABLE", "SUBSTITUTED", "CHAIN_BROKEN", "MODEL_MISMATCH") else HIGH
        findings.append(c.flag(
            ctx, f"Record {rec['sequence']} (position {r['position']}) is {r['status'].replace('_', ' ').lower()}. {r['explanation']}",
            sev, 0.99, AssetRef(type=AssetType.INFERENCE_RECORD, id=f"{rec['stream_id']}#{rec['sequence']}@{r['position']}"),
            metrics={"record_status": r["status"], "sequence": rec["sequence"], "position": r["position"], "failed_steps": [s["step"] for s in failed]},
            verification_steps=r["steps"], overrides=overrides))
    return findings


# ============================================================== Module 4: shift

def m4_mmd(c, ctx):
    b = _batch(ctx)
    ref = ctx.assets["input_batch"]
    if b == "ib_sector7_dawn":
        return [c.flag(ctx, "The dawn-patrol batch differs materially from the declared reference (northern plains, summer daylight): the embedding two-sample test rejects 'same distribution' with p < 0.001.",
                       MED, 0.9, ref, metrics={"mmd2": 0.084, "p_value": 0.001, "permutations": 1000, "effect_size": 1.46})]
    return [c.flag(ctx, "The relay batch differs from the reference only moderately overall (p = 0.002), but the difference is concentrated in a subset of images.",
                   MED, 0.7, ref, metrics={"mmd2": 0.031, "p_value": 0.002, "permutations": 1000, "effect_size": 0.52})]


def m4_desc(c, ctx):
    if _batch(ctx) == "ib_sector7_dawn":
        return [c.flag(ctx, "Images are darker (−1.9σ luminance), lower-contrast and softer than the reference, with a blue-grey colour cast - the signature of low sun and haze.",
                       MED, 0.85, ctx.assets["input_batch"], metrics={"luminance_d": -1.9, "contrast_d": -1.4, "sharpness_d": -1.2, "colour_temperature_d": 0.9})]
    return [c.flag(ctx, "Global brightness, colour and sharpness match the reference, but high-frequency spectral energy is 2.7σ above the reference noise profile in 14% of images.",
                   HIGH, 0.78, ctx.assets["input_batch"], metrics={"hf_band_energy_d": 2.7, "fraction_images_affected": 0.14, "luminance_d": 0.08})]


def m4_output(c, ctx):
    if _batch(ctx) == "ib_sector7_dawn":
        return [c.flag(ctx, "Model confidence has dropped from a mean of 0.87 to 0.74 and predictions are spread more evenly across classes - gradual degradation rather than a sharp change.",
                       MED, 0.7, ctx.assets["input_batch"], metrics={"mean_confidence_ref": 0.87, "mean_confidence_obs": 0.74, "class_js_divergence": 0.041})]
    return [c.flag(ctx, "29 images flip sharply to 'civilian_car' with high confidence, although their overall appearance is unchanged.",
                   HIGH, 0.84, ctx.assets["input_batch"], metrics={"sharp_flips": 29, "target_class": "civilian_car", "mean_flip_confidence": 0.93})]


def m4_calib(c, ctx):
    risk = 0.64 if _batch(ctx) == "ib_sector7_dawn" else 0.81
    return [c.flag(ctx, f"Calibrated probability that this shift is operationally harmful to the model: {risk:.2f} (isotonic calibration, ECE 0.041 on held-out scenarios).",
                   HIGH, risk, ctx.assets["input_batch"], metrics={"calibrated_risk": risk, "ece": 0.041, "extrapolated": False, "calibration_method": "isotonic"})]


def m4_verdict(c, ctx):
    if _batch(ctx) == "ib_sector7_dawn":
        return [c.flag(ctx, "Verdict: probable operational drift. The shift is broad, physically plausible (low light, haze) and consistent with the supplied dawn/haze metadata; no manipulation rule fired.",
                       MED, 0.78, ctx.assets["input_batch"], metrics={"verdict": "PROBABLE_OPERATIONAL_DRIFT", "rules_for": 4, "rules_against": 0})]
    return [c.flag(ctx, "Verdict: suspicious manipulation. The shift is localised to a subset, carries structured high-frequency energy inconsistent with sensor noise, and causes sharp flips toward one class.",
                   HIGH, 0.74, ctx.assets["input_batch"], metrics={"verdict": "SUSPICIOUS_MANIPULATION", "rules_for": 4, "rules_against": 1})]


def m4_meta(c, ctx):
    return []


def _has_acq_meta(ctx):
    if ctx.inputs["input_batch"].get("acquisition_metadata"):
        return True, ""
    return False, "no acquisition metadata (time, sensor, weather) supplied with this batch"


# ================================================================== registry

def build_registry() -> CheckRegistry:
    reg = CheckRegistry()
    M1, M2, M3, M4 = ModuleId.M1, ModuleId.M2, ModuleId.M3, ModuleId.M4
    NONE, BBL, BBS, WB = AccessLevel.NONE, AccessLevel.BB_L, AccessLevel.BB_S, AccessLevel.WB
    for c in [
        DemoCheck("M1.annot.sanity", M1, m1_sanity, inputs=("dataset",)),
        DemoCheck("M1.trigger.patch_repeat", M1, m1_patch, inputs=("dataset",), params={"min_repeat_count": 10, "patch_grid": "corners+4x4"}),
        DemoCheck("M1.trigger.hf_residual", M1, m1_hf, inputs=("dataset",), params={"blur_sigma": 2.0, "min_images": 10}),
        DemoCheck("M1.trigger.activation_cluster", M1, m1_cluster, inputs=("dataset",), params={"pca_dims": 10, "max_cluster_fraction": 0.15}),
        DemoCheck("M1.trigger.spectral", M1, m1_spectral, inputs=("dataset",), params={"outlier_percentile": 98.5}),
        DemoCheck("M1.flip.knn", M1, m1_knn, inputs=("dataset",), params={"k": 10, "min_disagreement": 0.9}),
        DemoCheck("M1.flip.confident", M1, m1_confident, inputs=("dataset",), params={"folds": 5, "min_probability": 0.9}),
        DemoCheck("M1.systematic.confusion", M1, m1_systematic, inputs=("dataset",), params={"alpha": 0.01, "correction": "holm"}, applicable=_has_meta),
        DemoCheck("M1.dup.phash", M1, m1_phash, inputs=("dataset",), params={"max_hamming": 6}),
        DemoCheck("M1.dup.embed", M1, m1_embed, inputs=("dataset",), params={"min_cosine": 0.97}),
        DemoCheck("M1.ood.knn", M1, m1_ood_knn, inputs=("dataset",), params={"k": 10, "threshold_percentile": 99}),
        DemoCheck("M1.ood.mahalanobis", M1, m1_ood_maha, inputs=("dataset",), params={"threshold_percentile": 99}),
        DemoCheck("M1.source_risk", M1, m1_source, inputs=("dataset",), params={"prior_alpha": 1, "prior_beta": 19, "p0": 0.02}, applicable=_has_meta),
        DemoCheck("M2.digest", M2, m2_digest, inputs=("model",)),
        DemoCheck("M2.structure", M2, m2_structure, access=WB, inputs=("model",)),
        DemoCheck("M2.fingerprint", M2, m2_fingerprint, access=BBL, inputs=("model", "battery"), params={"min_top1_agreement": 0.98}),
        DemoCheck("M2.reference_accuracy", M2, m2_refacc, access=BBL, inputs=("model", "battery")),
        DemoCheck("M2.trigger_reconstruction", M2, m2_recon, access=WB, inputs=("model", "battery"), fallback="M2.patch_probe",
                  applicable=_classification_only, params={"iterations": 400, "anomaly_threshold": 2.0, "time_budget_s": 120}),
        DemoCheck("M2.activation_stats", M2, m2_activation, access=WB, inputs=("model", "battery")),
        DemoCheck("M2.param_stats", M2, m2_params, access=WB, inputs=("model",), params={"max_severity": "MEDIUM"}),
        DemoCheck("M2.strip", M2, m2_strip, access=BBS, inputs=("model", "battery"), params={"superimpositions": 20, "entropy_threshold": 0.2}),
        DemoCheck("M2.patch_probe", M2, m2_probe, access=BBL, inputs=("model", "battery"), params={"probe_patches": 24}),
        DemoCheck("M3.record_verification", M3, m3_verify, inputs=("records",), params={"steps": 10, "freshness_window_days": 30}),
        DemoCheck("M4.mmd", M4, m4_mmd, inputs=("input_batch", "reference"), params={"permutations": 1000, "alpha": 0.01, "min_effect_size": 0.3}),
        DemoCheck("M4.descriptors", M4, m4_desc, inputs=("input_batch", "reference"), params={"min_abs_effect": 0.5}),
        DemoCheck("M4.output_shift", M4, m4_output, access=BBL, inputs=("input_batch", "reference", "model")),
        DemoCheck("M4.calibration", M4, m4_calib, access=BBL, inputs=("input_batch", "reference", "model"), params={"method": "isotonic", "harm_threshold": 0.05}),
        DemoCheck("M4.verdict", M4, m4_verdict, inputs=("input_batch", "reference")),
        DemoCheck("M4.metadata_consistency", M4, m4_meta, inputs=("input_batch",), applicable=_has_acq_meta),
    ]:
        reg.register(c)
    return reg
