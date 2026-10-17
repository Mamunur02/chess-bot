# 0018: Game-scoped external UCI opponents

Date: 2026-10-17. Status: implemented.

Extend the existing two-agent match manifest with `external_uci`; retain shared
budgets, colour pairs and automatic chess outcomes. Use python-chess for protocol
and rules. Add a defensive history-preserving board export rather than changing
the generic game protocol. Require a binary hash; record identity, option
defaults/overrides and separate asset hashes. Use one process per game, lazy
startup, explicit final cleanup and no silent engine retries or forfeits.

The installed SimpleEngine only times out play when `Limit.time` exists. Submit
the public asynchronous protocol play call on its own loop under `wait_for` so
depth/node searches also have a failure watchdog. Do not add a hidden UCI time
limit to depth/node budgets. Measure successful decisions only when requested;
enable this for external suites without changing existing deterministic records.

Retain external-suite source snapshots under ignored artifacts so dirty Git
runs are traceable. Keep compact measured summaries in Git, including the first
configuration failure. Exact timed decisions are not promised to reproduce.
No production dependency or learning framework is added.
