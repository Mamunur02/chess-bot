"""Create standalone figures from validated analysis JSON using Matplotlib.

Run in the isolated plotting environment; no change to the agent dependencies.
"""

import json
import sys
from importlib.metadata import distributions
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main() -> None:
    source = Path(sys.argv[1])
    data = json.loads(source.read_text())
    if data["status"] != "validated":
        raise ValueError("resolve integrity/repeat disagreements before plotting")
    variants = ["plain", "capture-ordering", "transposition-table", "quiescence-1"]
    labels = ["Plain", "Capture ordering", "Transposition table", "Quiescence (1)"]
    styles = ["o-", "s--", "^--", "D-."]
    figure, axes = plt.subplots(1, 3, figsize=(15, 4.8), layout="constrained")
    for variant, label, style in zip(variants, labels, styles, strict=True):
        rows = sorted(
            [r for r in data["variants"] if r["variant"] == variant],
            key=lambda r: r["budget"],
        )
        axes[0].plot(
            [r["budget"] for r in rows],
            [r["first_agreement_percent"] for r in rows],
            style,
            label=label,
        )
        timed = [r for r in rows if r["median_case_seconds"] is not None]
        axes[1].plot(
            [r["median_case_seconds"] for r in timed],
            [r["first_agreement_percent"] for r in timed],
            style,
            label=label,
        )
    axes[0].set(
        xscale="log",
        xlabel="Visited-node budget per move",
        ylabel="First-move solution agreement (%)",
        title="Quality versus nodes",
        ylim=(-2, 102),
    )
    axes[1].set(
        xlabel="Median case wall time (seconds)",
        ylabel="First-move solution agreement (%)",
        title="Quality versus runtime",
        ylim=(-2, 102),
    )
    contrasts = [r for r in data["contrasts"] if r["budget"] == 5000]
    for index, row in enumerate(contrasts):
        interval, estimate = (
            row["descriptive_95_percent_interval_pp"],
            row["complete_pair_delta_pp"],
        )
        if interval is None or estimate is None:
            continue
        # Draw interval endpoints directly: bootstrap intervals need not contain
        # the point estimate, so matplotlib's asymmetric-error widths may fail.
        axes[2].hlines(index, interval[0], interval[1], color="C0", linewidth=2)
        axes[2].plot(estimate, index, "o", color="C0")
    axes[2].axvline(0, color="0.5", linewidth=1)
    axes[2].set(
        yticks=range(len(contrasts)),
        yticklabels=[r["variant"] for r in contrasts],
        xlabel="Agreement change versus plain (percentage points)",
        title="Primary budget: 5,000 nodes",
    )
    axes[2].invert_yaxis()
    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(alpha=0.2)
    axes[0].legend(loc="best", fontsize=9)
    figure.suptitle(
        f"{data['positions']} {data['split']} positions; "
        f"{data['repeats']} timing passes\n"
        "First-pass quality; descriptive marginal paired 95% bootstrap intervals",
        fontsize=12,
    )
    for extension in ("png", "svg", "pdf"):
        figure.savefig(source.parent / f"quality-cost.{extension}", dpi=220)
    plt.close(figure)
    packages = sorted(f"{d.metadata['Name']}=={d.version}" for d in distributions())
    (source.parent / "plot-environment.txt").write_text("\n".join(packages) + "\n")


if __name__ == "__main__":
    main()
