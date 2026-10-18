# Opponent-dependence study: initial literature review

Reviewed 2026-10-18. Targeted initial review, not an exhaustive novelty search.
No empirical results or algorithmic novelty are claimed here.

## Closest methodological context

| Source | What it establishes | Consequence for this study |
| --- | --- | --- |
| Baxter, Tridgell and Weaver, TDLeaf(lambda), 1998 / arXiv 1999 | Combines TD learning and minimax search; contrasts learning at visited positions with learning through search-selected leaves. | Search-informed TD targets are established. Our proposed defensive target is not automatically TDLeaf and must be specified separately. |
| Wang et al., Balancing Safety and Exploitability in Opponent Modeling, AAAI 2011 | Studies the trade-off between exploiting an opponent and protecting payoff using uncertainty sets over opponent strategies. | Opponent exploitation versus defensive performance is established; we are not introducing that distinction. |
| Patterson, Liao and White, Robust Losses for Learning Value Functions, 2022, revised 2023 | Distinguishes clipped semi-gradient updates from principled robust Bellman-error objectives. | A Huber-style TD baseline must not be described as reproducing their full algorithm or inheriting its guarantees. |
| Littman, Markov Games as a Framework for Multi-Agent Reinforcement Learning, 1994 | Formulates competing-agent learning using Markov games and a minimax learning approach. | A worst-defence target changes the objective relative to averaging over a fixed opponent. |

Sources:

- https://arxiv.org/pdf/cs/9901001 (full five-page paper available; inspected search/TD definitions and experimental context).
- https://ojs.aaai.org/index.php/AAAI/article/view/7981 (abstract-level review; full algorithm comparison remains to do).
- https://arxiv.org/html/2205.08464v2 (inspected formulation and distinction between robust objectives and clipping).
- https://www.eecs.harvard.edu/cs286r/courses/spring06/papers/littman94markov.pdf (reference identified; detailed comparison remains to do).

## Defensible framing

A replication-inspired controlled investigation of opponent-distribution shift
in small neural chess value learning, comparing observed, mixed and defensive
targets under explicit compute limits. Clipping is no longer a core method.

Subsequent review identified a particularly close reference: Veness, Silver,
Uther and Blair, Bootstrapping from Game Tree Search (2009). Sections 1-3 discuss
dependence on opponent quality and motivate hypothetical search targets; the
paper also describes blunder-related workarounds in earlier KnightCap work.
This rules out framing opponent mistakes or defensive search targets as newly
identified ideas. Source inspected:
https://cgi.cse.unsw.edu.au/~blair/pubs/2009VenessSilverUtherBlairNIPS.pdf

Follow-up reading: Baxter, Tridgell and Weaver, Learning to Play Chess Using
Temporal Differences (2000), https://doi.org/10.1023/A:1007634325138 .
The short TDLeaf paper is not a substitute for reviewing this longer account.
The full experimental comparison matrix remains to be completed.

The candidate contribution is evidence from a controlled intervention on
opponent mistake frequency, with reference decision quality, transfer and
compute accounting. This is not yet a demonstrated gap. Before a final novelty
statement, inspect TDLeaf/KnightCap follow-up work, robust/adversarial Bellman
backups, and safe opponent-exploitation work for equivalent experiments.

## Why a lucky result is not automatically bias

For an illustrative one-decision game, suppose safe play guarantees a draw
(return 0), while risky play loses under defence (-1) but wins after a blunder
(+1). If blunder probability is p, its expected return is 2p-1. Preference for
risky play at p > 0.5 is correct against that opponent, even though it loses
against perfect defence. These are stipulated toy payoffs and algebra, not
measured chess outcomes. At p < 0.5 the same toy game does not predict risky
play after accurate learning. Therefore low blunder probabilities alone do not
guarantee an observable effect. Repeated opportunities and actual chess payoff
structure must be checked in development rather than assumed.

For a blended target with defensive weight beta, that toy risky value is
(1-beta)(2p-1)-beta. A reduced value is partly an explicit objective change,
not proof that the original estimator was statistically inconsistent.

## Reference-label semantics

python-chess Syzygy documentation describes WDL under the 50-move rule and
notes that direct WDL probing assumes a reset halfmove clock. DTZ, cursed wins,
blessed losses, captures/promotions and required successor tables matter.
Reference: https://python-chess.readthedocs.io/en/latest/syzygy.html

The current ChessState does not automatically claim 50-move or threefold draws.
Do not silently substitute Syzygy WDL for outcomes of that runner. Either use a
separately documented experiment-specific draw policy and compatible probing,
or explicitly limit claims to a defined reference metric. FEN cannot restore
pre-start repetition history. A short rollout cap is not a draw or a tablebase
outcome. These are protocol gates, not reasons to change the existing runner.
