"""Config loader: YAML -> read-only attribute tree, with cost-tag enforcement.

The honesty contract: every number under `costs:` must live inside a dict that
carries a `tag` in {VERIFIED, BROKER, ESTIMATE}. Loading fails loudly on an
untagged cost number, so an estimate can never silently masquerade as a
measured value.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

VALID_TAGS = {"VERIFIED", "BROKER", "ESTIMATE"}
# keys under costs: that are allowed to be plain (non-numeric) leaves
_COST_META_KEYS = {"tag", "note", "matrix_path", "news_calendar_json"}


class Cfg:
    """Read-only attribute/getitem access over a nested dict."""

    def __init__(self, d: dict[str, Any], _path: str = "cfg") -> None:
        object.__setattr__(self, "_d", d)
        object.__setattr__(self, "_path", _path)

    def __getattr__(self, key: str) -> Any:
        try:
            v = self._d[key]
        except KeyError:
            raise AttributeError(f"{self._path}.{key} missing from config") from None
        return Cfg(v, f"{self._path}.{key}") if isinstance(v, dict) else v

    __getitem__ = __getattr__

    def __setattr__(self, key: str, value: Any) -> None:
        raise TypeError("Cfg is read-only")

    def get(self, key: str, default: Any = None) -> Any:
        v = self._d.get(key, default)
        return Cfg(v, f"{self._path}.{key}") if isinstance(v, dict) else v

    def raw(self) -> dict[str, Any]:
        return self._d

    def __repr__(self) -> str:
        return f"Cfg({self._path}: {list(self._d)})"


def _check_cost_tags(node: Any, path: str) -> None:
    """Every numeric leaf under costs: must sit in a dict with a valid tag."""
    if not isinstance(node, dict):
        return
    numeric_keys = [k for k, v in node.items()
                    if isinstance(v, (int, float)) and not isinstance(v, bool)
                    and k not in _COST_META_KEYS]
    if numeric_keys:
        tag = node.get("tag")
        if tag not in VALID_TAGS:
            raise ValueError(
                f"config: {path} holds numbers {numeric_keys} but tag={tag!r}; "
                f"every cost number must be tagged one of {sorted(VALID_TAGS)}"
            )
    for k, v in node.items():
        if isinstance(v, dict):
            _check_cost_tags(v, f"{path}.{k}")
        elif isinstance(v, (int, float)) and not isinstance(v, bool) \
                and k not in _COST_META_KEYS and not numeric_keys:
            raise ValueError(f"config: bare cost number at {path}.{k} — wrap it "
                             f"in a dict with a tag")


def load_config(path: str | Path) -> Cfg:
    path = Path(path)
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(d, dict) and d, f"empty/invalid config at {path}"

    for section in ("data", "strategy", "pivots", "exits", "cpcv", "costs", "guards"):
        assert section in d, f"config missing section: {section}"

    costs = d["costs"]
    for k, v in costs.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            raise ValueError(f"config: bare cost number at costs.{k} — wrap it "
                             f"in a dict with a tag")
        _check_cost_tags(v, f"costs.{k}")

    assert d["strategy"]["variant"] in ("final", "base"), "strategy.variant must be final|base"
    assert d["pivots"]["day_boundary"] in ("utc00", "ny17"), "pivots.day_boundary must be utc00|ny17"
    assert d["exits"]["fill_mode"] in ("gap_open", "barrier_level"), \
        "exits.fill_mode must be gap_open|barrier_level"

    cfg = Cfg(d)
    # anchor relative paths to the config file's directory
    object.__setattr__(cfg, "_base_dir", path.parent)
    return cfg


def resolve_path(cfg: Cfg, rel: str) -> Path:
    """Resolve a config-relative path against the config file's directory."""
    p = Path(rel)
    if p.is_absolute():
        return p
    base = getattr(cfg, "_base_dir", Path.cwd())
    return (base / p).resolve()
