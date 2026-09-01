# Project purpose

Build a reproducible research platform for comparing game-playing methods,
beginning with chess infrastructure and classical baselines. The repository is
intended to support a rigorous Stats/ML/AI PhD application project.

# Required context

Read `CHESS_PROJECT_CODEX_IMPLEMENTATION_GUIDE.md` before planning a new
milestone. Check `docs/status.md` for current progress. Do not assume that
planned features are implemented.

# Current scope

The current phase is infrastructure and classical baselines unless the user
explicitly changes it. Do not introduce neural networks, large datasets,
self-play training, MCTS frameworks, an LLM layer, a GUI, or deployment as part
of an unrelated task.

# Research integrity

- Never invent or estimate experimental results and present them as measured.
- Distinguish plans, hypotheses, measurements, and conclusions.
- Do not claim novelty without evidence from a literature review.
- Record seeds, configurations, Git state, hardware, data versions, and
  failures for experiments.
- Prefer controlled comparisons under explicit node, simulation, depth, or
  time budgets.
- Keep benchmark and test data separate from data used for tuning.

# Engineering rules

- Inspect the repository and existing changes before editing.
- Preserve user changes and avoid unrelated rewrites.
- Make the smallest coherent change that satisfies the task.
- Use `python-chess` for chess rules and legal move generation.
- Do not build a custom legal-move generator.
- Keep the generic game protocol limited to requirements used by an existing
  implementation or an approved near-term milestone.
- Pass randomness explicitly; avoid hidden global random state.
- Prefer typed, documented Python for public interfaces.
- Ask before adding a production dependency unless the task explicitly
  requires it.
- Do not add empty modules or speculative architecture solely to match a future
  folder diagram.

# Tests

- Add or update tests for changed behaviour.
- Test game semantics and edge cases, not only happy paths.
- Keep the default test suite independent of GPUs, large downloads, internet
  access, and external engine binaries.
- Mark slower benchmark or integration tests clearly.

# Verification

Before declaring a coding task complete, run the relevant subset and normally:

```powershell
uv run pytest
uv run ruff check .
uv run mypy src
```

If a command cannot run, explain exactly why. Never claim a check passed when
it was not run.

# Completion report

Summarise:

1. Files changed.
2. Important design decisions.
3. Tests and checks run.
4. Known limitations or risks.
5. The next smallest sensible task.

Do not commit changes unless the user explicitly asks.
