# Decision 0008: Repetition-aware chess transposition key

Date: 2026-09-10

## Status

Accepted for Milestone 8.

## Context

The generic transposition table requires a key that captures every state detail
affecting future outcomes. Current FEN serialization includes the halfmove clock
but omits move history, so FEN alone cannot distinguish positions with different
automatic fivefold-repetition futures.

## Decision

- `ChessState.transposition_key()` returns an immutable, hashable value built
  only through public `python-chess` operations.
- Current position identity uses the first four FEN fields with legal en-passant
  normalization: piece placement, player to move, castling rights, and a legal
  en-passant square.
- The current halfmove clock is included for automatic seventy-five-move-rule
  semantics.
- Repetition context is represented by counts of normalized positions reached
  while replaying backward from the current board.
- The backward scan stops at the same `is_irreversible()` boundary used by
  `python-chess` repetition detection. History before that boundary cannot
  contribute to a future repetition count under those semantics.
- Fullmove number is excluded because it does not change legal actions or
  automatic terminal outcomes.
- The method operates on a private board copy and does not expose or mutate the
  adapter's board.
- The material alpha-beta agent exposes an explicit `transposition_table`
  flag, disabled by default, that supplies this key to generic search.

## Consequences

States reconstructed from the same FEN but lacking the same reversible history
can have different keys. Positions reached by different reversible move orders
also remain distinct when their historical repetition counts differ. Conversely,
different history before the same irreversible move is discarded when the
current position and subsequent history agree.

This key favors correctness over maximum cache reuse. Computing it replays the
reversible history at each keyed node, so its wall-clock cost may outweigh node
savings in shallow search. Node-count reductions and elapsed-time improvements
must therefore be measured separately before making performance claims.
