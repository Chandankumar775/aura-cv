"""Static and runtime enforcement of the non-negotiable rules (A3).

* rule 1: no network - the suite runs with sockets blocked; no URLs in runtime code;
* rule 7: no unpickling of untrusted files;
* rule 8: detectors never read Attack Lab ground truth;
* rule 9: "tamper-evident", never "tamper-proof".
"""

import re
import socket
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PY_SOURCES = sorted((ROOT / "aura").rglob("*.py"))


def test_non_loopback_sockets_are_blocked_in_the_suite():
    with pytest.raises(Exception) as exc:
        socket.create_connection(("192.0.2.1", 80), timeout=1)
    assert "SocketBlocked" in type(exc.value).__name__ or "blocked" in str(exc.value).lower()


def test_loopback_is_allowed():
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    try:
        socket.create_connection(srv.getsockname(), timeout=2).close()
    finally:
        srv.close()


def test_runtime_code_contains_no_urls():
    offenders = []
    for path in PY_SOURCES:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\bhttps?://", line):
                offenders.append(f"{path.relative_to(ROOT)}:{n}: {line.strip()}")
    assert not offenders, "network URLs in runtime code:\n" + "\n".join(offenders)


UNPICKLE = re.compile(r"\b(pickle|cPickle|dill|joblib)\.loads?\(|\bnp\.load\(.*allow_pickle\s*=\s*True")
TORCH_LOAD = re.compile(r"\btorch\.load\(")


def test_no_unpickling_paths():
    offenders = []
    for path in PY_SOURCES:
        text = path.read_text(encoding="utf-8")
        for n, line in enumerate(text.splitlines(), 1):
            if UNPICKLE.search(line):
                offenders.append(f"{path.relative_to(ROOT)}:{n}")
            if TORCH_LOAD.search(line) and "weights_only=True" not in line:
                offenders.append(f"{path.relative_to(ROOT)}:{n} torch.load without weights_only=True")
    assert not offenders, "\n".join(offenders)


def test_detectors_do_not_touch_ground_truth_manifests():
    detector_pkgs = ["m1_data", "m2_model", "m3_provenance", "m4_shift", "m5_governance", "core", "features", "adapters", "api"]
    offenders = []
    for pkg in detector_pkgs:
        for path in (ROOT / "aura" / pkg).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            # Only aura.eval may read manifests; M3 adds the manifest store to this list.
            if re.search(r"^\s*(from|import)\s+aura\.(eval|attack_lab\.manifests)\b", text, re.MULTILINE):
                offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, offenders


def test_never_claims_tamper_proof():
    banned = re.compile(r"tamper[- ]?proof|impossible to tamper", re.IGNORECASE)
    # CLAUDE.md and the prompt file quote the banned phrase in order to ban it.
    candidates = [*PY_SOURCES, *(ROOT / "schemas").glob("*.json"), *(ROOT / "docs").glob("*.md"), ROOT / "README.md"]
    offenders = []
    for path in candidates:
        if not path.exists():
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if banned.search(line) and not re.search(r"not tamper[- ]?proof|never .*tamper[- ]?proof|tamper-evident, not", line, re.IGNORECASE):
                offenders.append(f"{path.relative_to(ROOT)}:{n}: {line.strip()[:120]}")
    assert not offenders, "\n".join(offenders)
