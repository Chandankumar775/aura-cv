# Threat Model

Condensed from `docs/design.md` §4 (R-GEN-2). The trusted computing base below is a set
of **assumptions**, repeated in the coverage statement.

## Untrusted parties

| Party | May do |
|---|---|
| Data contributors | Submit mislabelled, duplicated, out-of-distribution or trigger-poisoned samples. One contributor may be malicious while others are honest. |
| Model suppliers | Supply a substituted or modified model, or one with a hidden backdoor. A pickled checkpoint could execute code on load, so AURA-CV never unpickles model files. |
| Anyone handling inference records after signing | Alter, replace, delete, reorder or replay records. |
| Operating environment | Produce inputs that drift from the reference distribution, or inject manipulated inputs. |

## Trusted computing base (assumptions)

1. AURA-CV code, bundled feature-extractor weights and the reference battery were obtained through a trusted channel and are unmodified.
2. The declared reference distribution is representative and not poisoned.
3. Signing keys (inference, audit, report) are generated and held in the trusted environment and are not compromised.
4. The inference host is trusted at the moment of signing; integrity holds from signing onward, not before.
5. A small trusted, correctly labelled reference set exists for calibration and the battery.

## Attacker capability assumed for evaluation

- Controls one or more contributors, but not all.
- May control the model supplier.
- Does not know AURA-CV's internal thresholds; adaptive attackers are out of scope.

## Controls implemented so far (M0)

| Threat | Control |
|---|---|
| Silent edit, deletion, reordering of audit history | Hash-chained, Ed25519-signed JSONL log; verification reports first failing entry |
| Tail truncation of the audit log | Comparison with an exported head hash / entry count |
| Cross-purpose key misuse (e.g. report key signing audit entries) | Keys bound to a purpose; verification checks purpose |
| A dependency phoning home | In-process outbound network guard; socket-blocked test suite |
| Checks quietly skipped under limited access | Scheduler emits an UNAVAILABLE finding for every check that cannot run |

The audit log is tamper-**evident**: changes are detectable, not impossible. An attacker
holding the audit private key can rewrite history (assumption 3).
