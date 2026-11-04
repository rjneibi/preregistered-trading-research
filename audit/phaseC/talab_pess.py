"""TA-LAB same-bar rerun. Builds two sandboxes on top of gap2, which already fills real gaps at the open. The stop was already tested before the target, so
the open ambiguity is a ladder or breakeven stop raised on a bar whose low also reaches it. pessA assumes the favourable extreme came first and exits at the
raised stop on that bar. pessB does not credit the raise on such a bar. Neither ordering is known from bars, so the worse of the two is the pessimistic figure."""
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
COPY = os.path.abspath(os.path.join(HERE, "..", "_copy")).replace(os.sep, "/")
SRC = COPY + "/rs_gap2/research/ta_lab"
OLD_TP = """                if gain_r >= 1.0 and sgn * (px - lock) > 0:
                    lock = px
"""
OLD_LAD = """                    if sgn * (new - lock) > 0:
                        lock = new
"""
A_TP = """                if gain_r >= 1.0 and sgn * (px - lock) > 0:
                    lock = px
                    if sgn * (adverse - lock) <= 0:
                        res, jx = sgn * (lock - px), j
                        break
"""
A_LAD = """                    if sgn * (new - lock) > 0:
                        lock = new
                        if sgn * (adverse - lock) <= 0:
                            res, jx = sgn * (lock - px), j
                            break
"""
B_TP = """                if gain_r >= 1.0 and sgn * (px - lock) > 0 and sgn * (adverse - px) > 0:
                    lock = px
"""
B_LAD = """                    if sgn * (new - lock) > 0 and sgn * (adverse - new) > 0:
                        lock = new
"""
for name, tp, lad in (("pessA", A_TP, A_LAD), ("pessB", B_TP, B_LAD)):
    dst = f"{COPY}/rs_{name}/research/ta_lab"
    assert not os.path.exists(dst), dst
    shutil.copytree(SRC, dst, ignore=shutil.ignore_patterns("__pycache__"))
    p = dst + "/lab.py"
    s = open(p, encoding="utf-8").read()
    assert OLD_TP in s and OLD_LAD in s
    open(p, "w", encoding="utf-8").write(s.replace(OLD_TP, tp).replace(OLD_LAD, lad))
    for f in os.listdir(dst):
        if f.endswith(".py"):
            q = dst + "/" + f
            t = open(q, encoding="utf-8", errors="surrogateescape").read()
            u = t.replace(f"{COPY}/rs_gap2/research/ta_lab", dst)
            if u != t:
                open(q, "w", encoding="utf-8", errors="surrogateescape").write(u)
    print(name, "ok")
