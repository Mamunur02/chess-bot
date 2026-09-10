# ADR 0011: Minimal synchronous UCI interface

## Status

Accepted.

## Context

The stronger classical baseline needs a standard engine boundary before adding
benchmark tooling. UCI is a text protocol, so a small command handler can
provide interoperability without a GUI, an external engine dependency, or a
research-policy decision.

A complete asynchronous UCI engine would require cancellation and concurrent
input handling. The current search is synchronous and has no cancellation
token. Adding threads only for protocol completeness would expand this baseline
milestone substantially.

## Decision

Add a `chesslab-uci` console entry point and a stateful, synchronous command
handler. The supported subset is:

- `uci`: emit engine name, contributor attribution, and `uciok`.
- `isready`: emit `readyok`.
- `ucinewgame`: restore the standard initial position.
- `position startpos [moves ...]`: rebuild a position from the initial state.
- `position fen <six fields> [moves ...]`: rebuild a position from FEN.
- `go depth N`: use `DepthBudget(N)`.
- `go nodes N`: use `NodeBudget(N)`.
- `go movetime N`: use `TimeBudget(N)` milliseconds.
- `stop`: accept the command when the handler is idle.
- `quit`: end the command loop.

Position updates are atomic. Every supplied move is parsed and applied to a
local state before it replaces the session state. Invalid positions therefore
leave the previous valid state intact.

Successful searches emit one `info` line and one `bestmove` line. The info
line reports completed depth, selective depth as principal-variation length,
centipawn or mate score, node count, optional elapsed milliseconds, and the
principal variation. Search errors emit an `info string error` diagnostic and
`bestmove 0000` so a caller is not left waiting for a move.

The console session uses the untuned `MaterialAlphaBetaAgent` defaults and an
explicitly seeded RNG. It does not silently enable move ordering, caching, or
quiescence.

## Consequences

- The baseline can be launched by tools that communicate through standard UCI
  input and output.
- UCI position histories are constructed through `ChessState.apply`, retaining
  repetition-relevant move history.
- The protocol layer reuses the existing typed budget and search-result
  contracts.
- Malformed commands and agent failures do not terminate the session.
- No additional production dependency is required.

Search execution blocks command processing. A `stop` sent while a search is
running cannot be read until that search has already returned, so this is not a
fully asynchronous or tournament-ready UCI implementation. Clock allocation
from `wtime`, `btime`, increments, and moves-to-go is also unsupported.
`setoption`, pondering, and `go infinite` are outside this baseline subset.

## Validation

Unit tests cover the handshake, readiness, stop and quit handling, start
positions, FEN positions, move application, atomic failure, all three supported
budget forms, malformed and unsupported commands, search failure, mate-score
formatting, new-game reset, and stream-loop termination. A real console-entry
smoke test verifies the installed command using a depth-one search.
