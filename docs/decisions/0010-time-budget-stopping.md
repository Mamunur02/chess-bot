# ADR 0010: Time-budget stopping

## Status

Accepted.

## Context

Depth and node budgets support controlled, deterministic comparisons, but a
classical engine also needs a practical wall-clock mode for later UCI use.
Wall-clock work varies with hardware, operating-system scheduling, and runtime
conditions, so it must not be presented as machine-independent or exactly
reproducible.

The deadline behaviour still needs deterministic unit coverage. Search must
also preserve its iterative-deepening contract when time expires midway
through an iteration.

## Decision

`TimeBudget` stores a positive integer number of milliseconds. Iterative
deepening samples an injected monotonic clock to establish a deadline, then
checks that deadline before entering every ordinary or quiescence node.
Production search uses `time.perf_counter`; tests supply a controlled clock.

Time-limited search follows the existing interruption rules:

- Nodes entered before expiration remain in cumulative statistics.
- A partial iteration never replaces the last fully completed iteration.
- If the deadline expires before root entry, search returns the first legal
  action, static root evaluation, depth zero, zero completed iterations, and
  zero visited nodes.
- The returned `elapsed_seconds` is measured from the initial clock sample
  through result construction.

The timer begins before root legal-action generation and ordering. Those
operations cannot be pre-empted, but their time counts toward the deadline.
Deadline checks occur only at node boundaries; an individual state operation
or evaluation can overrun the requested duration.

Depth and node budgets do not sample the supplied clock and retain
`elapsed_seconds=None`. This preserves their deterministic result equality.

Match metadata records time budgets with kind `milliseconds` and their integer
value. The material alpha-beta agent accepts an injectable clock and forwards
it to generic iterative deepening.

## Consequences

- Time budgets are suitable for practical engine operation, not exact
  cross-machine compute comparisons.
- Fixed-node budgets remain the preferred primary control when comparing
  search methods.
- Last-completed-depth semantics remain consistent across node and time
  interruptions.
- Tiny time budgets always yield a legal decision for a valid non-terminal
  root, even if no node can be entered.
- Clock injection keeps deadline edge cases fast and non-flaky in the default
  test suite.

The implementation does not use a background timer, threads, operating-system
signals, or cancellation inside evaluator and state calls. It does not claim
hard real-time guarantees.

## Validation

Tests cover invalid millisecond budgets, expiry after one completed iteration,
expiry before root entry, absence of clock sampling for non-time budgets,
material-agent clock forwarding, and serialized match metadata. The full suite
uses no sleeps and makes no assertions about host performance.
