"""Layer 3: product entity resolution (variant string -> product family).

Deterministic, provable merges only (auto-merge):
  1. OCR-confusable folding (0->O, 1->I applied to BOTH sides, so '1L' and 'IL' stay consistent)
  2. configured abbreviation expansion ('T/TISSUE' -> 'TOILET TISSUE')
  3. truncation: a shorter key that is a prefix of exactly one longer key
Fuzzy similarity NEVER auto-merges (pack-size variants score >0.95 yet are different products);
near-duplicates go to the human review queue instead. See docs/DECISIONS.md ADR-004.
"""
from __future__ import annotations

import difflib
import re
import hashlib
from dataclasses import dataclass

import pandas as pd

try:  # optional, faster and better; difflib fallback keeps the package dependency-light
    from rapidfuzz import fuzz as _fuzz

    def _similarity(a: str, b: str) -> float:
        return _fuzz.token_set_ratio(a, b) / 100.0

except Exception:  # pragma: no cover

    def _similarity(a: str, b: str) -> float:
        return difflib.SequenceMatcher(None, a, b).ratio()


_CONFUSABLES = str.maketrans({"0": "O", "1": "I"})


def fold(text: str) -> str:
    """Uppercase, fold OCR digit/letter confusions, collapse whitespace."""
    return re.sub(r"\s+", " ", str(text).upper().translate(_CONFUSABLES)).strip()


def expand(text: str, abbreviations: dict[str, str]) -> str:
    out = text
    # longest phrases first so 'W/UP LIQ' wins over shorter overlaps
    for k in sorted(abbreviations, key=len, reverse=True):
        out = re.sub(rf"(?<!\S){re.escape(fold(k))}(?!\S)", fold(abbreviations[k]), out)
    return out


def normalise(text: str, abbreviations: dict[str, str]) -> str:
    return expand(fold(text), abbreviations)


@dataclass
class ResolutionResult:
    catalogue: pd.DataFrame      # one row per canonical family
    variant_map: pd.DataFrame    # one row per raw string -> family_id
    review_pairs: pd.DataFrame   # unmerged near-duplicates for the human queue


def _slug(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")


def resolve_products(
    raw_counts: pd.Series,
    abbreviations: dict[str, str] | None = None,
    min_prefix_len: int = 20,
    fuzzy_review_threshold: float = 0.90,
) -> ResolutionResult:
    """raw_counts: index = raw product string, values = number of lines."""
    abbreviations = abbreviations or {}
    raw = pd.DataFrame({"raw_text": raw_counts.index.astype(str), "n_lines": raw_counts.values})
    raw["key"] = raw["raw_text"].map(lambda s: normalise(s, abbreviations))

    keys = raw.groupby("key")["n_lines"].sum().sort_values(ascending=False)
    key_list = list(keys.index)

    # Truncation: attach key k to the unique longer key that starts with it.
    parent: dict[str, str] = {k: k for k in key_list}
    ambiguous: list[tuple[str, list[str]]] = []
    for k in key_list:
        if len(k) < min_prefix_len:
            continue
        longer = [o for o in key_list if o != k and len(o) > len(k) and o.startswith(k)
                  and not (k[-1].isdigit() and o[len(k)].isdigit())]
        if len(longer) == 1:
            parent[k] = longer[0]
        elif len(longer) > 1:
            ambiguous.append((k, longer))

    def root(k: str) -> str:
        while parent[k] != k:
            k = parent[k]
        return k

    raw["root_key"] = raw["key"].map(root)
    raw["merge_reason"] = "exact"
    raw.loc[raw["key"] != raw["raw_text"].map(str.upper), "merge_reason"] = "fold/abbrev"
    raw.loc[raw["root_key"] != raw["key"], "merge_reason"] = "truncation"

    fam = []
    used = set()
    for rk, grp in raw.groupby("root_key"):
        top = grp.sort_values("n_lines", ascending=False).iloc[0]
        fid = _slug(rk)
        if fid in used:
            fid += "-" + hashlib.sha256(rk.encode()).hexdigest()[:8]
        used.add(fid)
        fam.append(
            {
                "family_id": fid,
                "family_key": rk,
                "family_name": top["raw_text"].strip(),
                "n_lines": int(grp["n_lines"].sum()),
                "n_variants": int(len(grp)),
                "variants": sorted(grp["raw_text"]),
                # deterministic merges are exact-by-construction; confidence reflects how far we reached
                "confidence": 1.0 if len(grp) == 1 else (0.98 if set(grp["merge_reason"]) <= {"exact", "fold/abbrev"} else 0.95),
            }
        )
    catalogue = pd.DataFrame(fam).sort_values("n_lines", ascending=False).reset_index(drop=True)
    variant_map = raw.merge(catalogue[["family_id", "family_key", "confidence"]], left_on="root_key", right_on="family_key")[
        ["raw_text", "n_lines", "family_id", "merge_reason", "confidence"]
    ]

    # Review queue: near-identical but UNMERGED families (never auto-merged).
    pairs = []
    ids = dict(zip(catalogue["family_key"], catalogue["family_id"]))
    keys_l = list(catalogue["family_key"])
    for i, a in enumerate(keys_l):
        for b in keys_l[i + 1 :]:
            s = _similarity(a, b)
            if s >= fuzzy_review_threshold:
                pairs.append({"family_a": ids[a], "family_b": ids[b], "similarity": round(s, 3)})
    for k, longer in ambiguous:
        pairs.append({"family_a": _slug(k), "family_b": ";".join(_slug(x) for x in longer), "similarity": 1.0})
    review = pd.DataFrame(pairs, columns=["family_a", "family_b", "similarity"])
    return ResolutionResult(catalogue, variant_map, review)
