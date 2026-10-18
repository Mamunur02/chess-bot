# Resume checkpoint

STOPPED FOR USAGE LIMIT. The latest readout was 3% five-hour remaining / 85%
weekly remaining. The preceding check was 13%; concurrent task usage crossed
the requested 10% boundary between polls. No further implementation is authorized
in this session. On resume check limits first and avoid concurrent agents close
to the reserve. Do not use the account reset credit without permission.

Final state: foundation commit85a8b00 is pushed. Subsequent neural/interaction,
audit/pilot scripts, tests and environment manifest remain LOCAL AND UNCOMMITTED.
No pilot or training process was launched. All implementation agents finished.
The structural audit was invoked with output
`artifacts/opponent-dependence-v1/partition-audit-v1.json`; inspect whether that
report completed, and rerun to a fresh output if interrupted.

IMPORTANT first repair: latest full pytest FAILED DURING COLLECTION at
`tests/test_endgame_pilot.py:8`, `ModuleNotFoundError: No module named 'scripts'`.
Use the existing importlib file-loader pattern in `tests/test_endgame_audit.py`
instead of assuming the repository root is on pytest's import path. This fix
has NOT been made. Ruff check . and mypy src passed in that same invocation;
shell exit0 reflected the last command, NOT a passing pytest run.

Neural finite-gradient/parameter/validation guards were repaired; 9 isolated
CPU neural tests passed, including durable NaN failure regressions. The pilot
script is UNREVIEWED and UNRUN; its author reported a limitation: top-level
failure status is written but a failed/interrupted per-method record may stay
`running`. Repair/test that before launching it. Author's standalone mypy check
of the pilot script failed; do not conflate mypy src with a checked pilot script.
Author reported13 pilot tests passing under a different invocation, but the
required full-suite invocation failed as above. Preserve this discrepancy.

Updated 18 October 2026. User instruction: monitor account usage and stop when
either usage window reaches 10% remaining. Do not consume a reset credit without
permission. At the first check, five-hour remaining was 27%, weekly 89%.
Check current limits before resuming; these values are historical.

## Authority and repository

Read `AGENTS.md`, the implementation guide, `docs/status.md`, and authoritative
`docs/research/opponent-dependence-protocol-v1.md`. The user explicitly authorized
the neural research phase, Luna implementation with Astra scientific review,
normal commits/pushes, and autonomous local work. The user reconfirmed Git
authorization directly in chat after automatic approval review initially rejected
the attachment's authorization. Never force push or purchase cloud resources.

Branch: `codex/opponent-dependence`, tracking existing GitHub origin
`https://github.com/Mamunur02/chess-bot.git`.
Foundation checkpoint `85a8b00` is committed and pushed.
Use command-scoped `git -c safe.directory=C:/Projects/chess-bot ...` under the
sandbox; do not change global security settings. Git writes require escalation.

Preexisting edits to README, practical-project-scope, and untracked historical
scope/draft/decisions documents must be preserved. The approved protocol,
literature and status record were included in the foundation checkpoint.

## Completed and measured

- Experiment-only automatic draw claims and full-history branches; original
  general runner unchanged. Theoretical queries ignore history and clocks.
- Canonical identity, split ownership, named RNGs, serial table acquisition,
  generator, 775 encoder, opponent, replay and pure targets implemented/tested.
- Eight tables downloaded into ignored `data/syzygy/protocol-v1`, whole-file
  SHA-256 verified. Pinned source notices and hashes are in the committed
  acquisition manifest. Optional real-table tests passed; embedded trailer
  comparison is not checksum recomputation.
- Both development screens passed: KRvKR 1,822/2,000, KQvKR 1,192/2,000
  decision-sensitive/worsening positions. KRvKR selected by fixed rule.
- Five KRvKR partitions generated under
  `artifacts/opponent-dependence-v1/krvkr-partitions/`; independent structural
  audit is the next gate. No final prediction/playing metrics have been inspected.
- CPU PyTorch 2.7.0+cpu and NumPy 2.5.4 installed only in ignored
  `artifacts/neural-env`. Package versions are in
  `experiments/manifests/endgame-neural-cpu-environment.json`.
- Neural architecture and interaction driver implemented; isolated neural,
  interaction and target checks passed 35 tests. Further failure-accounting
  repairs and audit/pilot scripts are in progress and not in the first commit.
- Latest full suite: 395 passed, 2 skipped before subsequent additions;
  targeted replay/target checks: 22 passed; Ruff and mypy passed on foundation.

Hardware: i7-10875H, 16,954,482,688 bytes RAM, RTX2070 Max-Q 8192 MiB,
driver566.36. GPU PyTorch and GPU timing not verified. Cash spending GBP0;
electricity not estimated. No full training matrix or charged resources launched.

## Next actions

1. Inspect Git state and current files; do not assume the in-progress files below
   are complete. Review `neural.py`, `interaction.py`, `scripts/audit_endgame_partitions.py`
   and `scripts/run_endgame_pilot.py` plus their tests.
2. Confirm neural pretraining explicitly fails on nonfinite gradients, parameters
   or validation MSE instead of silently restoring an old checkpoint.
3. Run structural partition audit without printing final labels or tuning on them.
4. Review and run seed9001 development-only bounded pilot, <=512 decisions per
   beta at p=.5, same initial checkpoint; warmup256, batch32, every8 transitions.
   Measure complete training cost and failures; don't select by method outcome.
5. Optimize batching/caching only with semantics preserved, if needed. Freeze
   largest feasible common budget among 2000/5000/10000/20000 using full core
   projection <=36 machine-hours including30% contingency and GBP60. No full
   matrix before this gate. Keep all five seeds; final labels remain sealed.
6. Continue protocol sequence; reserve 31 October–1 November for reporting.

## Commands

```powershell
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe pytest --basetemp artifacts/pytest-NEW-UNIQUE-NAME
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe ruff check .
uv --cache-dir artifacts/uv-cache run --no-sync --python .venv/Scripts/python.exe mypy src
artifacts/neural-env/Scripts/python.exe -m pytest tests/test_endgame_neural.py -q
```

Full tests need execution outside the sandbox for existing Windows UCI subprocess
tests. `--no-sync` avoids unnecessary build-network access; locked sync was
successfully refreshed after registering the integration marker. For real tables,
set `CHESSLAB_SYZYGY_DIRECTORY=data/syzygy/protocol-v1` and run
`tests/test_endgame_tables.py`. Default tests skip optional Torch/table integrations.

No background experiment should be assumed from this file. At checkpoint creation,
data-generation processes had finished and no pilot/training process was running.
Subagent sessions are transient; resume from actual files and records, not an
assumption that those sessions continue after the chat stops.
