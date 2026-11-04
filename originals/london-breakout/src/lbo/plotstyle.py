"""Matplotlib styling from the reference data-viz palette (light and dark renders)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

THEMES = {
    "light": dict(surface="#fcfcfb", text="#0b0b0b", text2="#52514e", muted="#898781", grid="#e1e0d9",
                  series=["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
                  mid="#f0efec", pos="#2a78d6", neg="#e34948"),
    "dark": dict(surface="#1a1a19", text="#f0efec", text2="#c3c2b7", muted="#898781", grid="#2c2c2a",
                 series=["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
                 mid="#383835", pos="#3987e5", neg="#e66767"),
}


def apply(theme):
    t = THEMES[theme]
    plt.rcParams.update({
        "figure.facecolor": t["surface"], "axes.facecolor": t["surface"], "savefig.facecolor": t["surface"],
        "text.color": t["text"], "axes.labelcolor": t["text2"], "axes.edgecolor": t["grid"],
        "xtick.color": t["muted"], "ytick.color": t["muted"], "axes.grid": True, "grid.color": t["grid"],
        "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
        "axes.prop_cycle": matplotlib.cycler(color=t["series"]), "lines.linewidth": 2.0,
        "font.size": 9.5, "axes.titlesize": 10.5, "axes.titleweight": "bold", "legend.frameon": False,
        "legend.labelcolor": t["text2"],
    })
    return t


def diverging(theme):
    t = THEMES[theme]
    return LinearSegmentedColormap.from_list("div", [t["neg"], t["mid"], t["pos"]])
