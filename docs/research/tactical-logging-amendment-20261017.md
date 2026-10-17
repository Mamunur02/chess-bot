# Operational logging amendment, 2026-10-17

The initial study and nine whole-process recovery attempts encountered Windows
access-denied failures while atomically replacing `metadata.json`. Recovery v1
exhausted its retry limit with 2,235 saved cases. Repeated process restarts did
not address contention at the individual write operation.

The user explicitly requested fixing the problem and resuming. The project
artifact writer now retries only Windows access/sharing errors (5, 32, 33) during
the same atomic replacement, with bounded exponential backoff: 16 attempts,
less than six seconds total requested sleep. It preserves the previous valid
JSON and cleans temporary files on failure; unrelated errors propagate without
retry. This does not change exclusive creation of new case files. A real Win32
reader denying deletion/replacement reproduces the issue and passes with the
fix; simulated persistent/unrelated errors also have regression coverage.

The identity of the actual process holding the production file lock is unknown.
The reproduced sharing scenario demonstrates the handled failure mode; it does
not identify an antivirus, editor, or other process as the culprit.

## Reproducibility

Do not rewrite the original experiment plan, frozen protocol or source snapshot.
`scripts/resume_tactical_study_v2.py` verifies all original source/lock hashes,
allows only the new working-tree artifact-writer change, then imports the
original engine/runner from the copied source tree. It replaces only the
runner's artifact-writer alias with the separately copied amended writer.
The repository argument points at the original copied source tree, keeping
the original resume guard and source identity intact. This is a disclosed
runtime logging override, not a claim that every executed function is unchanged.

`artifacts/tactical-test-v1/recovery-v2/amendment.json` records the original plan
digest, old/new writer hashes, launcher hash, user authorization and saved-case
count. The amendment writer/launcher sources and the previous failure/session
metadata are retained beside it. Analysis verifies these hashes and includes
the amendment and its sources in the generated report bundle.

Search algorithms, evaluator, labels, node budgets, seeds and schedule remain
unchanged. Existing case files are neither overwritten nor rerun. Logging is
outside the measured per-case search duration, but backoff, interruptions,
restarts and warmups may indirectly affect thermal/cache state. Retain all
timing observations and disclose this limitation rather than excluding cases.

The original quiet-window deadline remains 18:51 BST. No extra paid compute,
dependency, algorithm change, protocol rewrite or Git commit was introduced.
