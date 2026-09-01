# Decision 0001: Game and agent contracts

Date: 2026-09-01

## Status

Accepted for Milestone 1.

## Context

The first contracts must support a `python-chess` adapter and later controlled
comparisons on simpler deterministic games. They are not intended to model all
possible environments.

## Decision

- `GameState.apply` returns a logically new state and must leave its parent
  unchanged from the caller's perspective. Implementations may choose their
  own safe internal representation.
- Players have stable integer identities `0` and `1`. `current_player` means
  the player whose turn is next. Each game adapter must document how its native
  players map to these identities.
- Terminal returns are ordered `(player_0, player_1)`. A win is `1.0`, a loss
  is `-1.0`, and a draw is `0.0`, so returns are zero-sum. Calling `returns()`
  on a non-terminal state raises `ValueError`.
- Actions are generic and unconstrained. A game chooses its own action type;
  the shared contract does not assume chess moves, integers, or hashability.
- An agent receives a caller-owned `random.Random`. Implementations must not
  silently use module-global random state.
- Search budgets initially support positive depth and node limits. Time and
  simulation budgets will be added when an implemented experiment requires
  them.
- An `AgentDecision` initially contains only the selected action. Scores,
  search statistics, principal variations, and metadata will be added when a
  concrete agent can produce and test them.

For terminal states, `legal_actions()` returns an empty sequence. Applying an
illegal action raises `ValueError`. Agents are called on non-terminal states.

## Excluded scope

The contracts do not support chance nodes, simultaneous actions, imperfect
information, multiplayer games, generic environment wrappers, chess-specific
rules, or concrete search algorithms.

## Consequences

The small interface is sufficient for the next chess-adapter milestone and a
test-only deterministic game. Additional concepts require a demonstrated use
case and an explicit extension rather than speculative fields or methods.
