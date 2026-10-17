# First learned bot: input needed

Prepared 2026-10-17 after external matches and shared tactical comparisons.
These are proposals, not implemented methods or measured learning results. No
dataset has been selected for training and no new dependency has been installed.
This decision chooses the next small implementation, not a permanent thesis topic.

## Recommended first slice: our own supervised evaluator

Keep the existing alpha-beta search and learn a position evaluation from a small,
separate set of engine-labelled positions. Start with a regularized linear model
over explicit board features, then consider a small neural model only if useful.
This makes the learned component, search budget and inference overhead separately
inspectable. It is a proposed engineering starting point, not a claim that a
linear model will improve chess performance.

Use a bounded local CPU pilot with a hard labelling cap. Choose and record the
position-generation policy, score perspective, label engine/settings/node budget,
mate handling, target transform and loss before creating labels. Engine scores
must have a consistent perspective; python-chess provides
[PovScore](https://python-chess.readthedocs.io/en/latest/engine.html#chess.engine.PovScore).
Ridge regression would minimize squared prediction error plus an L2 coefficient
penalty; see the [official model definition](https://scikit-learn.org/stable/modules/linear_model.html#ridge-regression-and-classification).
This is a candidate objective, not an authorization to install scikit-learn.

Split source games/trajectories before extracting positions, and deduplicate
connected position groups across splits. All puzzles and game-start fixtures
already used here remain evaluation/development fixtures, not training examples.
Freeze a fresh test set before validation tuning. Compare label error and bot
decisions separately; lower label error does not establish stronger play.
Keep terminal mate/draw utility outside the learned heuristic. Record checkpoint,
feature schema and dataset hashes; compare identical search switches under
explicit node and time budgets, including inference cost.

Training linear algebra may need an additional package such as NumPy. A small
coefficient model could use ordinary Python for inference, keeping that package
in an optional training environment. Package choice remains pending; any new
production dependency still requires approval. No GPU, paid API or paid compute
is proposed.

## Alternatives

| First task | What we would build/use | Additional decisions |
| --- | --- | --- |
| Own supervised evaluator (recommended) | Train a position-value model, reuse existing search | Teacher targets, board features, label budget, group splits, training dependency |
| Human-move policy | Predict a played legal move from a human-game corpus | Player population/rating/time control, game source/license, cross-entropy target, source-game splits, move decoding/search |
| Existing trained comparator | Use a compatible published engine/model through UCI | Exact implementation/model/license/hashes and CPU settings; does not mean we trained it |

Stockfish already provides an external NNUE/search reference. Adopting another
pretrained comparator does not by itself build our own learned bot. RL/self-play
and an LLM bot remain later choices; rewards, data reuse and costs would require
their own bounded plan.

Required user input now: choose the first task. The exact small pilot protocol
can then be made concrete before data generation/training, keeping numerical
training tools isolated from the production agent where practical.
