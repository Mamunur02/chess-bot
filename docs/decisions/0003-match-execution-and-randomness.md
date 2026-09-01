# Decision 0003: Match execution and randomness

Date: 2026-09-01

## Status

Accepted for Milestone 3.

## Context

Matches must be deterministic under a recorded seed, reject illegal agent
decisions, distinguish completion from operational stops, and serialize actions
without coupling the generic runner to chess.

## Decision

- Agents are supplied as a two-element tuple indexed by stable player identity.
- A root `random.Random` derives and records one 128-bit seed for each player.
  Each agent receives its own RNG, so one player's random draws cannot perturb
  the other player's stream.
- `RandomAgent` chooses uniformly from legal actions using only the supplied
  RNG. It accepts but ignores the search budget because it performs no search.
- Both players receive the same explicit search budget for a match.
- The runner validates an action against the state's legal actions before
  encoding or applying it. A record is appended only after both operations
  succeed.
- Callers supply an action-to-string encoder. Match records therefore remain
  JSON-compatible without requiring the runner to understand game-specific
  actions such as UCI chess moves.
- Completed matches alone contain terminal returns. A ply-limit stop is
  `interrupted`; agent, illegal-action, encoding, and state errors are `failed`.
  None of these non-completed states is reported as a draw.
- Invalid runner configuration raises `ValueError`. Runtime match errors are
  captured as structured failures. `BaseException` subclasses such as
  `KeyboardInterrupt` and `SystemExit` are not caught.
- Match metadata records the root seed, derived player seeds, budget, and ply
  limit. Timestamps, Git state, hardware, agent versions, run IDs, and aggregate
  metrics belong to a later experiment-logging layer.
- Ply indices are zero-based and equal their positions in the move sequence.

## Consequences

Repeated matches with identical inputs and deterministic agents reproduce the
same random streams and records. Results remain honest about incomplete or
failed execution. Game-specific serialization stays at the call site, and the
runner remains usable with chess and simpler deterministic games.
