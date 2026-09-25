#!/usr/bin/env python3
"""Wait for an unoccupied assigned GPU, then run resumable E6 jobs sequentially."""
import argparse
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
E6 = HERE.parent
sys.path.insert(0, str(HERE))
from run_e6 import log


def gpu_free(index: int) -> bool:
    rows = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=index,memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
        text=True,
    ).strip().splitlines()
    for row in rows:
        i, memory, utilization = [int(x.strip()) for x in row.split(",")]
        if i == index:
            return memory < 1024 and utilization < 10
    return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--gpu", type=int, required=True)
    p.add_argument("--models", nargs="+", required=True)
    p.add_argument("--folds", default="ABCD")
    a = p.parse_args()
    log(f"GPU {a.gpu} queue start: {a.models}")
    for model in a.models:
        for fold in a.folds:
            for variant in ("full_sequence",):
                while True:
                    try:
                        if gpu_free(a.gpu):
                            # Another experiment may briefly release memory
                            # between folds. Require a stable idle interval.
                            log(f"GPU {a.gpu} tentatively free; verify again after 60 s")
                            time.sleep(60)
                            if gpu_free(a.gpu):
                                break
                    except Exception as exc:
                        log(f"GPU {a.gpu} probe error: {exc!r}")
                    log(f"GPU {a.gpu} occupied; check again in 30 min; pending {model} fold {fold} {variant}")
                    time.sleep(1800)
                out = E6 / "results" / model / f"fold_{fold}" / variant
                out.mkdir(parents=True, exist_ok=True)
                command = [sys.executable, "-u", str(HERE / "run_e6.py"), "--model", model,
                           "--fold", fold, "--variant", variant, "--gpu", str(a.gpu)]
                log(f"GPU {a.gpu} start {model} fold {fold} {variant}")
                with (out / "run.log").open("a", encoding="utf-8") as f:
                    result = subprocess.run(command, stdout=f, stderr=subprocess.STDOUT, cwd=E6.parents[2])
                if result.returncode != 0:
                    log(f"GPU {a.gpu} FAILED {model} fold {fold} {variant}: exit {result.returncode}; see {out/'run.log'}")
                    return result.returncode
                subprocess.run([sys.executable, str(HERE / "run_e6.py"), "--stage", "summarize"], cwd=E6.parents[2], check=True)
    log(f"GPU {a.gpu} queue complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
