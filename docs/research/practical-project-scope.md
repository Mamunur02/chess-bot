# Practical chess-bot comparison scope

Clarified directly by the user on 2026-10-17. This supersedes the requirement to
choose one narrow learning research question before continuing useful setup.

## Goal

Build a chess bot, compare it with existing bots and bots using other methods,
and evaluate the differences with useful metrics. Start simple; add learned,
RL/self-play and possibly LLM-based methods progressively. The research question
is still developing. Do not independently redirect the project into engine
optimisation or demand a fully specified thesis before making comparisons work.

Different methods may be implemented, adapted or used as existing trained
opponents. Clearly identify which code/model was built or trained here and which
is a third-party reference. Comparing an existing trained bot does not require
reproducing its entire training pipeline. Do not promise all methods trained
from scratch within one week.

## What exists and what is missing

| Component | Actual state | Relevant next work |
| --- | --- | --- |
| Own bot | Random, material-greedy and material alpha-beta agents implemented | Use these as working bots and simple controls |
| Evaluation | Shared internal/external tactical first-move agreement, runtime/node diagnostics and colour-paired matches implemented | Add the chosen learned method; retain failure denominators |
| External opponents | UCI server plus pinned external UCI agents in matches and tactical comparisons, with lifecycle/failure/provenance records | Use the same bridge for a compatible learned comparator if chosen |
| Evaluation data | Versioned 50/50/200 Lichess puzzle splits; 200-position test already evaluated | Preserve original result; use fresh test data for later tuned comparisons |
| Ordinary-game comparison starts | Two versioned development opening starts; completed four-game colour-paired Stockfish 19 smoke | Broaden starts before making strength claims |
| Learning data | No human-game policy dataset, engine-labelled value dataset or replay/training pipeline prepared | Prepare the appropriate small dataset when a first learned method is chosen |
| RL/self-play and LLM methods | Not implemented | Add a bounded method or compatible existing bot when ready; define objectives/budgets first |

## Immediate implementation sequence

1. Completed: connect external UCI opponents to the match/evaluation workflow.
   Stockfish 19 is now locally pinned and used as the first existing reference. `python-chess` already provides the UCI client API;
   no universal agent framework is needed. Preserve board history, clean up
   subprocesses, record engine identity/binary/network versions/options and test
   failures with mocked engines. Keep default tests binary/network independent.
2. Completed: run a small smoke comparison of the existing bot with that reference, using
   explicit settings and colour-swapped starts. Then produce one understandable
   comparison table: game outcomes, tactical agreement, decision runtime,
   compute settings and failures. Do not infer a calibrated Elo from a few games.
3. Add one learned bot or existing learned comparator, then reuse the same
   evaluation. Choose its target/loss/data before training, without treating that
   choice as the permanent direction of the whole project.
4. Extend to RL/self-play and possibly LLM implementations as bounded comparisons,
   rather than building every training system in advance. Keep resource costs
   and contribution claims explicit.

The existing one-week target means a modest working comparison is the priority.
Do not spend the week preparing speculative infrastructure for every method.
The precise research question can sharpen through the comparisons and reading.

## Dataset roles

- Puzzle positions: shared move-quality evaluation, not a general training corpus.
- Opening/start positions: controlled head-to-head comparisons and colour swaps.
- Human-game PGNs: possible policy-learning data, split by source game before
  extracting positions. No large download is needed before choosing that method.
- Engine-labelled positions: possible value-learning data, with explicit score
  perspective, label budget and disjoint source groups. Not currently prepared.
- Self-play trajectories: produced by a chosen learning loop; terminal reward,
  discounting and any shaping must be explicit. Not an existing dataset here.
- LLM evaluation: a shared position/game set plus legal-move constraints, model
  version, prompts, token/time/cost budgets and error records. No API purchase
  or LLM model choice is currently authorized.

The source candidates are the official Lichess exports, not an assumption that
every dataset is interchangeable: https://database.lichess.org/

## Fair comparisons

Keep tactical quality and efficiency as the initial emphasis; add head-to-head
outcomes alongside them. Time budgets and hardware/resource settings matter
across unlike engines: their node counts and reported depths are not universal
units of equal computation. Human-move prediction and best-play agreement also
answer different questions. Modern Stockfish uses NNUE; label it as hybrid
search/neural evaluation rather than a purely handcrafted classical comparator.

Sources checked 2026-10-17:

- UCI client API: https://python-chess.readthedocs.io/en/latest/engine.html
- Stockfish evaluation: https://official-stockfish.github.io/docs/nnue-pytorch-wiki/docs/nnue.html

Existing constraints remain: local compute first, optional free Colab, no paid
compute beyond explicit approval after a pilot, no new production dependency
without authorization, and no Git commits without request. Engine/model/data
adoption and new training remain concrete choices made when needed, not blanket
authority inferred from the broad list of potential methods.

Implementation update 2026-10-17: steps 1 and the ordinary-game portion of step 2
are complete. See `../external-opponents.md` and the measured external-engine
summary. External tactical agreement and learned training remain future work.
The current user explicitly authorized committing and pushing reviewed work;
that supersedes the earlier no-commit instruction in this historical scope note.

Implementation update for milestone 19: shared internal/external tactical
evaluation is now implemented and a 40-case development smoke is complete.
The ten inputs were already observed; fresh confirmatory data remain necessary.
The remaining method decision is documented in `first-learned-bot-decision.md`.
