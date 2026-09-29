"""Demo inference-record stream: genuinely signed records, deliberately tampered copies,
and a real verifier (R-INF-1, R-INF-2; CLAUDE.md A8.3; scenarios I1-I6).

The records are real Ed25519-signed RFC 8785 objects produced with the local inference
key; only the model outputs inside them are illustrative. Tampering is applied to the
demo copy after signing, and verification recomputes everything from scratch.
"""

from __future__ import annotations

import base64
import copy
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from aura.core.canonical import canonicalize
from aura.core.hashing import ZERO_DIGEST, sha256_bytes, sha256_canonical
from aura.core.ids import format_ts, parse_ts
from aura.core.types import KeyPurpose, RecordStatus
from aura.demo.catalog import CLASSES, REGISTERED_WEIGHT_DIGEST, fake_digest
from aura.m3_provenance.keys import KeyStore, UnknownKeyError

STREAM_ID = "uav-07-cam-front"
N_RECORDS = 240

CONFIG = {
    "preprocessing": {"resize": [224, 224], "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225], "channel_order": "RGB"},
    "inference": {"runtime": "torchscript-cpu", "runtime_version": "2.4.1", "score_precision": 4, "top_k": 3},
}
REGISTERED_CONFIG_DIGEST = sha256_canonical(CONFIG)
MODEL_REF = {"id": "mdl_vehnet_v21", "format": "torchscript", "weight_digest": REGISTERED_WEIGHT_DIGEST}

# Tampering plan: sequence -> scenario (I1..I6).
PLAN = {
    57: "I1-alter-class",
    91: "I1-alter-score",
    133: "I5-forge-unknown-key",
    170: "I2-substitute",
    210: "I4-delete",
    225: "I6-model",
    231: "I6-config",
}
REPLAYS = {120: 64, 201: 150}  # insert, after position of seq k, a replay of seq v

EXPLAIN = {
    RecordStatus.VERIFIED: "All checks passed: the record is exactly as signed, in sequence, and bound to the registered model and configuration.",
    RecordStatus.ALTERED: "The signature does not match the record contents: the record was modified after it was signed.",
    RecordStatus.UNVERIFIABLE: "The record names a signing key that is not registered here, so it cannot be verified and must not be accepted.",
    RecordStatus.SUBSTITUTED: "A validly signed record from a different stream was placed here in place of the original.",
    RecordStatus.REPLAYED: "This record repeats an earlier sequence number and nonce: it is a replay of a record already seen.",
    RecordStatus.CHAIN_BROKEN: "The link to the previous record and the sequence number do not match: one or more records were removed or reordered.",
    RecordStatus.MODEL_MISMATCH: "The record is genuine but was produced by a model whose weight digest differs from the registered model.",
    RecordStatus.CONFIG_MISMATCH: "The record is genuine but the preprocessing or inference configuration differs from the registered one.",
    RecordStatus.INPUT_MISMATCH: "The supplied image does not hash to the input digest bound in the record.",
}


def _sign(store: KeyStore, record: dict, key_id: str | None = None) -> dict:
    body = {k: v for k, v in record.items() if k != "signature"}
    data = canonicalize(body)
    if key_id is None:
        key_id, sig = store.sign(KeyPurpose.INFERENCE, data)
    else:
        sig = store.sign_with(key_id, data)
    return {**body, "signature": sig}


def record_hash(record: dict) -> str:
    return sha256_bytes(canonicalize({k: v for k, v in record.items() if k != "signature"}))


def _output(rng: random.Random) -> dict:
    scores = [rng.random() ** 3 for _ in CLASSES]
    top = rng.randrange(len(CLASSES))
    scores[top] += 2.5
    total = sum(scores)
    ranked = sorted(((round(s / total, 4), c) for s, c in zip(scores, CLASSES)), reverse=True)[:3]
    return {"top_k": [{"class": c, "score": s} for s, c in ranked]}


def build_stream(store: KeyStore, seed: int = 1337) -> list[dict]:
    """Return the demo stream as imported from the field (tampering already applied)."""
    rng = random.Random(seed)
    key = store.require_active(KeyPurpose.INFERENCE)
    t0 = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=15, hours=3)
    genuine: list[dict] = []
    prev = ZERO_DIGEST
    for seq in range(1, N_RECORDS + 1):
        model = dict(MODEL_REF)
        config = copy.deepcopy(CONFIG)
        if PLAN.get(seq) == "I6-model":
            model["weight_digest"] = fake_digest("vehnet-r18-unregistered.pt")
        if PLAN.get(seq) == "I6-config":
            config["inference"]["score_precision"] = 2
        rec = {
            "record_version": "1.0",
            "stream_id": STREAM_ID,
            "sequence": seq,
            "timestamp": format_ts(t0 + timedelta(seconds=seq * 7 + rng.random())),
            "nonce": "b64:" + base64.b64encode(rng.randbytes(16)).decode(),
            "input": {"sha256": sha256_bytes(f"frame-{seq}".encode()), "width": 1920, "height": 1080, "encoding": "jpeg"},
            "model": model,
            "config": {**config, "sha256": sha256_canonical(config)},
            "output": _output(rng),
            "prev_record_hash": prev,
            "signer": {"key_id": key.key_id, "algorithm": "Ed25519"},
        }
        rec = _sign(store, rec)
        prev = record_hash(rec)
        genuine.append(rec)

    # Build the imported (tampered) copy - operates on copies, never the genuine list.
    stream: list[dict] = []
    for rec in genuine:
        seq = rec["sequence"]
        scenario = PLAN.get(seq)
        r = copy.deepcopy(rec)
        if scenario == "I4-delete":
            continue
        if scenario == "I1-alter-class":
            present = {t["class"] for t in r["output"]["top_k"]}
            r["output"]["top_k"][0]["class"] = next(c for c in ["civilian_car", "truck", "apc", "tank", "pickup"] if c not in present)
        elif scenario == "I1-alter-score":
            r["output"]["top_k"][0]["score"] = 0.9981
        elif scenario == "I5-forge-unknown-key":
            r["signer"]["key_id"] = "inference-20260911-7c1e02aa"
            r["signature"] = "b64:" + base64.b64encode(rng.randbytes(64)).decode()
        elif scenario == "I2-substitute":
            other = copy.deepcopy(genuine[seq - 40])
            other["stream_id"] = "uav-03-cam-rear"
            other["sequence"] = seq
            r = _sign(store, {k: v for k, v in other.items() if k != "signature"})
        stream.append(r)
        if seq in REPLAYS:
            stream.append(copy.deepcopy(genuine[REPLAYS[seq] - 1]))
    return stream


# ------------------------------------------------------------------ verifier


def _step(name: str, passed: bool | None, detail: str) -> dict:
    return {"step": name, "passed": passed, "detail": detail}


REQUIRED = {"record_version", "stream_id", "sequence", "timestamp", "nonce", "input", "model", "config", "output", "prev_record_hash", "signer", "signature"}


def verify_record(
    store: KeyStore,
    rec: dict,
    *,
    expected_stream: str,
    anchor_hash: str | None,
    expected_seq: int | None,
    seen_nonces: set[str],
    last_ts: str | None,
) -> tuple[RecordStatus, list[dict]]:
    steps: list[dict] = []
    missing = REQUIRED - set(rec)
    steps.append(_step("1. Schema", not missing, "all bound fields present" if not missing else f"missing: {', '.join(sorted(missing))}"))
    if missing:
        return RecordStatus.ALTERED, steps

    body = canonicalize({k: v for k, v in rec.items() if k != "signature"})
    key_id = rec["signer"].get("key_id", "")
    try:
        sig_ok = store.verify(key_id, body, rec["signature"], purpose=KeyPurpose.INFERENCE)
        steps.append(_step("2. Signature", sig_ok, f"Ed25519 under {key_id}: " + ("valid" if sig_ok else "does NOT match record contents")))
        unknown = False
    except UnknownKeyError:
        sig_ok, unknown = False, True
        steps.append(_step("2. Signature", False, f"key {key_id} is not in the key registry"))

    if anchor_hash is None:
        steps.append(_step("3. Hash chain", None, "previous record failed verification; link not checkable"))
        chain_ok = True
    else:
        chain_ok = rec["prev_record_hash"] == anchor_hash
        steps.append(_step("3. Hash chain", chain_ok, "prev_record_hash links to the previous record" if chain_ok else "prev_record_hash does not match the previous record"))

    seq = rec["sequence"]
    repeat = expected_seq is not None and seq < expected_seq
    gap = expected_seq is not None and seq > expected_seq
    steps.append(_step("4. Sequence", not (repeat or gap), f"sequence {seq}" + (f" repeats (expected {expected_seq})" if repeat else f" skips ahead (expected {expected_seq})" if gap else " follows +1")))

    nonce_reused = rec["nonce"] in seen_nonces
    steps.append(_step("5. Nonce", not nonce_reused, "nonce is unique in this stream" if not nonce_reused else "nonce was already used by an earlier record"))

    ts_ok = last_ts is None or parse_ts(rec["timestamp"]) >= parse_ts(last_ts)
    steps.append(_step("6. Timestamp", ts_ok, rec["timestamp"] + (" is monotonic" if ts_ok else " is earlier than the previous record")))

    model_ok = rec["model"].get("weight_digest") == REGISTERED_WEIGHT_DIGEST
    steps.append(_step("7. Model digest", model_ok, "matches registered VehNet-R18 v2.1" if model_ok else "weight digest is not the registered model"))

    cfg = {k: v for k, v in rec["config"].items() if k != "sha256"}
    cfg_ok = rec["config"].get("sha256") == sha256_canonical(cfg) == REGISTERED_CONFIG_DIGEST
    steps.append(_step("8. Config digest", cfg_ok, "matches registered configuration" if cfg_ok else "configuration differs from the registered one"))
    steps.append(_step("9. Input hash", None, "source image not supplied with this import; not performed"))
    steps.append(_step("10. Re-execution", None, "not requested for this assessment"))

    if unknown:
        status = RecordStatus.UNVERIFIABLE
    elif not sig_ok:
        status = RecordStatus.ALTERED
    elif rec["stream_id"] != expected_stream:
        status = RecordStatus.SUBSTITUTED
    elif repeat or nonce_reused:
        status = RecordStatus.REPLAYED
    elif not chain_ok or gap:
        status = RecordStatus.CHAIN_BROKEN
    elif not model_ok:
        status = RecordStatus.MODEL_MISMATCH
    elif not cfg_ok:
        status = RecordStatus.CONFIG_MISMATCH
    else:
        status = RecordStatus.VERIFIED
    return status, steps


def verify_stream(store: KeyStore, stream: list[dict], expected_stream: str = STREAM_ID) -> list[dict]:
    """Verify every record in file order. Returns [{position, record, status, steps}]."""
    out = []
    anchor: str | None = ZERO_DIGEST
    expected_seq: int | None = 1
    nonces: set[str] = set()
    last_ts: str | None = None
    for pos, rec in enumerate(stream):
        status, steps = verify_record(
            store, rec, expected_stream=expected_stream, anchor_hash=anchor, expected_seq=expected_seq, seen_nonces=nonces, last_ts=last_ts
        )
        out.append({"position": pos, "record": rec, "status": status.value, "steps": steps, "explanation": EXPLAIN[status]})
        if status is RecordStatus.REPLAYED:
            continue  # an inserted extra: the chain continues from the genuine record
        nonces.add(rec.get("nonce", ""))
        expected_seq = rec.get("sequence", 0) + 1
        last_ts = rec.get("timestamp", last_ts)
        if status in (RecordStatus.ALTERED, RecordStatus.UNVERIFIABLE, RecordStatus.SUBSTITUTED):
            anchor = None  # true predecessor hash unknown
        else:
            anchor = record_hash(rec)
    return out


def verify_single(store: KeyStore, rec: dict) -> dict:
    """Signature/field check of one (possibly locally edited) record: tamper demo panel."""
    status, steps = verify_record(store, rec, expected_stream=STREAM_ID, anchor_hash=None, expected_seq=None, seen_nonces=set(), last_ts=None)
    return {"status": status.value, "steps": steps, "explanation": EXPLAIN[status]}
