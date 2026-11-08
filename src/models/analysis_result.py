"""Data classes describing analysis candidates and reports."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

CONFIDENCE_LEVELS = ("none", "low", "medium", "high")


@dataclass
class Candidate:
    """One possible interpretation of the input bytes, with explainable scoring."""

    method: str
    kind: str
    output: bytes
    text: Optional[str]
    printable_ratio: float
    decoding_errors: int
    quality: float
    prior: float
    score: float
    confidence: str
    entropy: float
    stats: dict[str, Any] = field(default_factory=dict)
    explanation: list[str] = field(default_factory=list)
    key: Optional[bytes] = None

    def output_hex(self, limit: int = 256) -> str:
        shown = self.output[:limit].hex(" ")
        return shown + (f" … (+{len(self.output) - limit} bytes)" if len(self.output) > limit else "")

    def preview(self, limit: int = 120) -> str:
        if self.text is not None:
            flat = self.text.replace("\n", "⏎ ").replace("\r", "")
            return flat[:limit] + ("…" if len(flat) > limit else "")
        return self.output_hex(limit // 3)

    def describe(self, text_limit: int = 4000) -> str:
        lines = [
            f"Method: {self.method}",
            f"Score: {self.score:.3f}  (quality {self.quality:.3f} × method prior {self.prior:.2f})",
            f"Confidence: {self.confidence}",
            f"Printable-character ratio: {self.printable_ratio:.1%}",
            f"Decoding errors (UTF-8): {self.decoding_errors}",
            f"Output length: {len(self.output)} bytes   Entropy: {self.entropy:.3f} bits/byte",
        ]
        if self.key is not None:
            shown = self.key.decode("utf-8", "replace") if all(32 <= b < 127 for b in self.key) else "(non-printable)"
            lines.append(f"Key: hex {self.key.hex()}  text {shown}")
        lines.append("Why this rank:")
        lines += [f"  - {e}" for e in self.explanation]
        if self.text is not None:
            lines += ["", "Output as text:", self.text[:text_limit] + ("…" if len(self.text) > text_limit else "")]
        lines += ["", "Output as hex:", self.output_hex()]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method, "kind": self.kind, "score": self.score, "quality": self.quality,
            "prior": self.prior, "confidence": self.confidence,
            "printable_ratio": round(self.printable_ratio, 4), "decoding_errors": self.decoding_errors,
            "entropy": round(self.entropy, 4), "key_hex": self.key.hex() if self.key else None,
            "text": self.text[:4000] if self.text is not None else None,
            "output_hex": self.output[:4096].hex(), "explanation": list(self.explanation),
        }


@dataclass
class AnalysisReport:
    """Complete result of a local analysis run."""

    input_info: dict[str, Any] = field(default_factory=dict)
    byte_stats: dict[str, Any] = field(default_factory=dict)
    encoding_checks: list[str] = field(default_factory=list)
    signatures: list[str] = field(default_factory=list)
    compression: list[str] = field(default_factory=list)
    key_lengths: list[tuple[int, float]] = field(default_factory=list)
    candidates: list[Candidate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reliable: list[str] = field(default_factory=list)
    uncertain: list[str] = field(default_factory=list)
    inconclusive: bool = True

    def to_text(self) -> str:
        out: list[str] = []

        def section(title: str, lines: list[str]) -> None:
            if lines:
                out.append(f"== {title} ==")
                out.extend(lines)
                out.append("")

        section("Input", [f"{k}: {v}" for k, v in self.input_info.items()])
        section("Byte statistics", [f"{k}: {v}" for k, v in self.byte_stats.items()])
        section("Encoding checks", self.encoding_checks)
        section("File signatures", self.signatures or ["none recognised"])
        section("Compression checks", self.compression)
        if self.key_lengths:
            section("Best repeating-key lengths (lower distance = more likely)",
                    [f"length {n}: {d:.3f} bits/byte" for n, d in self.key_lengths[:6]])
        section("Warnings", [f"! {w}" for w in self.warnings])
        verdict = "INCONCLUSIVE - no interpretation reached medium or high confidence." if self.inconclusive \
            else "At least one interpretation reached medium/high confidence (see candidates)."
        section("Verdict", [verdict])
        section("Reliable conclusions", [f"+ {r}" for r in self.reliable])
        section("Uncertain / not proven", [f"? {u}" for u in self.uncertain])
        return "\n".join(out).rstrip() + "\n"

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_info": self.input_info, "byte_stats": self.byte_stats,
            "encoding_checks": self.encoding_checks, "signatures": self.signatures,
            "compression": self.compression, "warnings": self.warnings,
            "reliable": self.reliable, "uncertain": self.uncertain,
            "inconclusive": self.inconclusive,
            "candidates": [c.to_dict() for c in self.candidates],
        }
