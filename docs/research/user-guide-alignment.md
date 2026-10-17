# User research intent and guide alignment

Date: 2026-10-17.

Later user clarification: the practical aim is to build a bot and compare
methods/existing opponents, with the research question still developing. A
precise learning question is not required before useful shared setup continues.
See `practical-project-scope.md`, which supersedes the narrow question gate below.

## Direct user instruction

This is the user's Stats/ML/AI PhD application project, including research and
experimentation with an ML technique. Do not select an independent research
direction or treat engineering optimisation as the main research objective.
The previous efficiency-versus-quality-assessment menu is superseded, not chosen.

## Supplied reference

Read all 31 pages of
`C:/Users/mamun/Downloads/Self-Study Chess Bot Project for a PhD Application.pdf`.
It is reference material, not blanket implementation authority. Suggestions,
expected outcomes and timelines are not user instructions, measured results or
approval to implement every branch, install dependencies or spend money.

- Pages 1-2 place the classical baseline within a learning/hybrid platform.
- Pages 24-25 distinguish infrastructure and classical ablations from supervised
  policy learning and supervised value learning/NNUE-style evaluation.
- Page 25 proposes engine-labelled positions and a learned evaluator compared
  with handcrafted evaluation inside the same searcher. It also proposes human
  move prediction. Neither is a confirmed user choice yet.
- Pages 26-27 describe simpler-game self-play, chess self-play, searchless models
  and optional LLM tool use. They are alternatives/extensions, not selected work.
- Page 27's suggested three-experiment sequence includes a classical baseline,
  learned evaluator inside search and optional LLM tool interface. This is the
  document's recommendation, not an instruction to implement an LLM layer now.
- Pages 27-28 describe a six-month programme. Its estimates and anticipated
  improvements are not promises for this repository or the current week.

## Current position and next gate

The repository's rules, classical agents, reproducible evaluation and first
held-out tactical/search-cost study provide the baseline foundation. No learned
model or training/RL experiment has been implemented. The baseline study does
not substitute for the intended ML research component.

Clarify the user's intended learning question/technique before selecting a model,
target, dataset or milestone. Learned evaluation inside the current searcher is
explicitly in the guide, but must not be assumed to be the selected branch.
Follow any particular hypothesis, technique or paper the user already intends.

Then scope one experiment: question and classical control; learned target,
perspective and loss (or explicit reward/discounting/shaping if RL); data/labels
and disjoint splits; minimal training design; controlled evaluation; development
pilot, compute estimate and stopping criteria. Any further infrastructure work
must directly enable that agreed experiment.

Existing constraints persist: target approximately 2026-10-24, local compute
first, optional free Colab, and at most GBP 50 only after careful checks. The
completed test set is now observed: do not train/tune on it and then call it
held out. No unselected neural/RL/LLM implementation is authorized by this PDF.
