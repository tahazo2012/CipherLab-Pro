"""Transparent candidate scoring and ranking.

    score = quality * prior

* quality - how text-like (or structurally valid) the output is, 0..1 (see core.statistics)
* prior   - how plausible the *method* is a priori. Methods that can "succeed" on
            almost any input (XOR, Latin-1, reversal) get lower priors so they cannot
            outrank a plain valid decoding without much better evidence.

Confidence bands: <0.35 none, <0.60 low, <0.80 medium, otherwise high; then capped for
methods and sample sizes where statistics cannot justify more.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

from src.core.statistics import printable_ratio, score_text, shannon_entropy
from src.models.analysis_result import CONFIDENCE_LEVELS, Candidate

PRIORS: dict[str, tuple[float, str]] = {
    "raw": (1.0, "direct reading of the bytes; no transformation assumed"),
    "container": (0.95, "recognised file signature or valid compressed container"),
    "transform": (0.90, "standard encoding layer (Base64/hex/URL/...) found inside the bytes"),
    "utf16": (0.70, "UTF-16 decoding can accept many byte patterns by accident"),
    "xor1": (0.80, "single-byte XOR is a guess: 255 keys were tried, so a lucky match is possible"),
    "xorN": (0.70, "repeating-key XOR is a guess with many degrees of freedom"),
    "latin1": (0.40, "Latin-1 accepts every byte sequence, so success alone proves nothing"),
    "reverse": (0.50, "byte reversal is a speculative transformation"),
}


@dataclass(frozen=True)
class ScoringContext:
    persian_enabled: bool = True
    persian_table: Optional[Mapping[str, float]] = None


def confidence_for(score: float, kind: str, length: int) -> tuple[str, Optional[str]]:
    """Return (confidence, cap_note)."""
    level = 0 if score < 0.35 else 1 if score < 0.60 else 2 if score < 0.80 else 3
    cap, why = 3, None
    if kind == "latin1":
        cap, why = 1, "capped at 'low': Latin-1 never fails to decode"
    elif kind in ("xor1", "xorN", "reverse"):
        if length < 16:
            cap, why = 1, "capped at 'low': fewer than 16 bytes cannot support a statistical claim"
        elif length < 32 or kind != "xor1":
            cap, why = 2, "capped at 'medium': a statistical guess cannot prove which key/method was really used"
    if level > cap:
        level = cap
    else:
        why = None
    return CONFIDENCE_LEVELS[level], why


def build_candidate(method: str, output: bytes, *, kind: str, ctx: ScoringContext,
                    text: Optional[str] = None, key: Optional[bytes] = None,
                    structural: Optional[float] = None, structural_note: str = "",
                    extra: Optional[dict] = None) -> Candidate:
    """Score one interpretation and attach a full explanation."""
    prior, prior_why = PRIORS[kind]
    if text is None:
        try:
            text = output.decode("utf-8")
        except UnicodeDecodeError:
            text = None
    errors = 0 if text is not None else output.decode("utf-8", "replace").count("\ufffd")
    explanation = [f"Method '{method}' has prior {prior:.2f}: {prior_why}."]
    text_quality = 0.0
    if text is not None:
        res = score_text(text, persian_enabled=ctx.persian_enabled, persian_table=ctx.persian_table)
        text_quality = res.score
        explanation.append(f"Text-likeness ({res.language}) = {res.score:.3f}: " + "; ".join(res.notes) + ".")
    else:
        explanation.append(f"Output is not valid UTF-8 ({errors} invalid sequence(s)), so it has no text score.")
    pr = printable_ratio(output)
    if structural is not None:
        quality = max(structural, text_quality)
        explanation.append(f"Structural evidence: {structural_note} (quality {structural:.2f}).")
    elif text is not None:
        quality = text_quality
    else:
        quality = round(pr * 0.25, 4)
        explanation.append(f"Binary output: quality limited to printable ratio × 0.25 = {quality:.3f}.")
    score = round(quality * prior, 4)
    conf, cap_note = confidence_for(score, kind, len(output))
    explanation.append(f"score = quality {quality:.3f} × prior {prior:.2f} = {score:.3f} → confidence '{conf}'.")
    if cap_note:
        explanation.append(cap_note + ".")
    stats = {"length": len(output)}
    if extra:
        stats.update(extra)
    return Candidate(method=method, kind=kind, output=output, text=text, printable_ratio=pr,
                     decoding_errors=errors, quality=round(quality, 4), prior=prior, score=score,
                     confidence=conf, entropy=shannon_entropy(output), stats=stats,
                     explanation=explanation, key=key)


def rank_candidates(candidates: list[Candidate], limit: int = 25) -> list[Candidate]:
    """Sort best-first, drop duplicate XOR outputs, and record each candidate's rank."""
    ordered = sorted(candidates, key=lambda c: (c.score, c.prior), reverse=True)
    seen: set[tuple[bytes, bool]] = set()
    unique: list[Candidate] = []
    for cand in ordered:
        sig = (cand.output, cand.kind in ("xor1", "xorN"))
        if sig in seen:
            continue
        seen.add(sig)
        unique.append(cand)
    unique = unique[:limit]
    for i, cand in enumerate(unique, 1):
        cand.explanation.append(f"Ranked #{i} of {len(unique)} by score (ties broken by method prior).")
    return unique
