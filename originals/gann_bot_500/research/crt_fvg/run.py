"""CRT-FVG-1: python run.py [grid|select|full|analyse|report] (no argument = all, in order).
`full` opens the OOS data and refuses to run twice."""
import sys

from crt_fvg import pipeline as P

STAGES = ["grid", "select", "full", "analyse", "report"]

if __name__ == "__main__":
    for s in (sys.argv[1:] or STAGES):
        print("==", s, flush=True)
        if s in ("analyse", "report"):
            from crt_fvg import analyse
            getattr(analyse, s)()
        else:
            getattr(P, "stage_" + s)()
