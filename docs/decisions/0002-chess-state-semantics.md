# Decision 0002: Chess state semantics

Date: 2026-09-01

## Status

Accepted for Milestone 2.

## Context

The chess adapter must implement the generic game-state contract without
duplicating chess rules or exposing mutable state that can corrupt a search
tree. Optional draw claims also need an explicit interpretation.

## Decision

- `python-chess` owns board representation, move generation, move validation,
  move application, repetition tracking, and terminal-outcome rules.
- `ChessState` owns a private `chess.Board`. It never exposes that mutable board.
- `ChessState.apply()` checks legality, copies the board and its complete move
  stack, pushes the move on the copy, and returns a new state. The parent is
  unchanged.
- Public actions are `chess.Move` values.
- White is player 0 and Black is player 1. Terminal returns remain ordered by
  these stable identities.
- Outcomes use `Board.outcome(claim_draw=False)`. Checkmate, stalemate,
  insufficient material, the seventy-five-move rule, and fivefold repetition
  are automatic terminal outcomes. Claimable fifty-move and threefold draws
  are not automatic.
- Draw claims are not represented as chess moves. A future match runner may
  add an explicit claim policy if an experiment requires one.
- FEN construction validates the resulting position. FEN preserves board
  fields and move counters but cannot reconstruct repetition history because
  it contains no move stack.
- Routine initial-position perft tests cover depths 0 through 3. Depth 4 has
  the standard count 197,281 but is excluded from the default suite to keep
  feedback fast.

## Consequences

The adapter supplies stable research semantics while delegating chess
correctness to a maintained library. States created by applying moves retain
repetition history; an equivalent state reconstructed from FEN may not have the
same repetition outcome. Optional draw-claim behavior remains an explicit
future match-policy decision rather than a hidden environment rule.
