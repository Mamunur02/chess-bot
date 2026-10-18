# Endgame development screen

Both protocol-v1 development screens completed on 18 October 2026. KRvKR is
selected by the prespecified preference rule. No neural comparison informed
this choice.

| Family | Seed | Positions | Decision-sensitive | Worsening available | Pass |
| --- | ---: | ---: | ---: | ---: | --- |
| KRvKR | 1101 | 2,000 | 1,822 | 1,822 | Yes |
| KQvKR | 1201 | 2,000 | 1,192 | 1,192 | Yes |

The two counts coincide because a legal action worsens the best category exactly
when legal actions have different q values. Each threshold is 100. These are
uniform-placement development samples, not a distribution of ordinary games.
The two-million-proposal cap was not reached. A second-family learning study
remains contingent on the doubled resource projection.

Local raw data and manifests are in
`artifacts/opponent-dependence-v1/development/`. Each manifest records the source
hashes, baseline Git commit and dirty state, generation seed, proposal/rejection
counts, dataset hash, Python/chess versions and verified table hashes.
The table acquisition record is
`experiments/manifests/syzygy-protocol-v1-acquisition.json`.

Reproduce the screen with a fresh output directory:

```powershell
uv run python -m chesslab.endgames.dataset --tablebase-dir data/syzygy/protocol-v1 --acquisition-manifest experiments/manifests/syzygy-protocol-v1-acquisition.json --output-dir artifacts/endgame-screen-reproduction
```

The opt-in real-table test passed SHA-256 and embedded trailer comparisons and
theoretical Bellman checks on fixed positions and colour exchanges. Comparing
the embedded trailer is not recomputing the generator's CityHash-based checksum;
whole-file integrity was verified against the publisher's SHA-256 list.
Default tests use mocks and need neither downloads nor PyTorch. No experimental
training outcome, playing-strength gain, budget feasibility or novel method is
claimed from this screen.
