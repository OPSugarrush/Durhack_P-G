"""CLI:  python -m needstate <command>

  audit          data audit + entity resolution summary
  analyse        run the full stack and export CSVs to data/processed
  validate       injection study (detection floor + false alarms)
  missing-data   corruption grid (needs ~minutes at full size)
"""
from __future__ import annotations

import argparse
import json


def main() -> None:
    ap = argparse.ArgumentParser(prog="needstate")
    ap.add_argument("command", choices=["audit", "analyse", "validate", "missing-data"])
    ap.add_argument("--config", default="configs/pipeline.yaml")
    ap.add_argument("--out", default="data/processed")
    ap.add_argument("--quick", action="store_true", help="fewer trials/levels for a fast smoke run")
    a = ap.parse_args()

    if a.command == "audit":
        from needstate.pipeline import run

        r = run(a.config)
        print(json.dumps(r.audit, indent=2, default=str))
        c = r.resolution.catalogue
        print(f"\nraw variants: {r.resolution.variant_map.shape[0]}  ->  families: {len(c)}")
        print(f"unmerged near-duplicate pairs queued for review: {len(r.resolution.review_pairs)}")
    elif a.command == "analyse":
        from needstate.service import analyse, export

        an = analyse(a.config)
        for p in export(an, a.out):
            print("wrote", p)
        s = an.trends["family"]
        print(f"\nfamily trends: {int(s['significant'].sum())} significant of {len(s)} (FDR). "
              f"{int((s['p_perm'] < .05).sum())} nominal p<.05; approximately {0.05 * len(s):.0f} expected under a complete null.")
        print(f"within-consumer-null pairs significant: {int((an.pairs['q'] < .05).sum())} of {len(an.pairs)}")
        print("consumer concentration:", {k: round(v, 4) for k, v in an.routines_summary.items()})
    elif a.command == "validate":
        from needstate.pipeline import run
        from needstate.validation_harness import injection as inj

        r = run(a.config)
        print(json.dumps(inj.false_alarm_rate(r.lines), indent=2))
        print(inj.trend_recovery(r.lines, n_trials=4 if a.quick else 12).to_string(index=False))
    else:
        from needstate.missing_data.evaluation import run_experiment
        from needstate.pipeline import run

        r = run(a.config)
        levels = (0.1, 0.3) if a.quick else (0.05, 0.1, 0.2, 0.3)
        df = run_experiment(r, r.config, levels=levels, progress=lambda f: print(f"\r{f:.0%}", end=""))
        from pathlib import Path

        Path(a.out).mkdir(parents=True, exist_ok=True)
        df.to_csv(Path(a.out) / "missing_data_experiment.csv", index=False)
        print("\n", df.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
