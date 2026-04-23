#!/usr/bin/env python3
"""
Generate synthetic OCR-style documents for benchmarking openai/privacy-filter.

Document templates live in templates/<doctype>.py.  Any module there that defines
both DOC_TYPE and generate() is auto-registered — no changes needed here to add
a new document type.

Output JSON schema per record:
  { id, text, pii_gt, non_pii_data, metadata }
"""

import argparse
import json
import random
from dataclasses import dataclass, asdict
from datetime import date

from faker import Faker

from templates import REGISTRY
from templates.base import fmt_date, word_count

# ---------------------------------------------------------------------------
# Locale distribution for 50 samples — adjust weights here as needed
# ---------------------------------------------------------------------------
_BASE_LOCALE_SPECS = (
    [("en_US", None)] * 16
    + [("en_IN", None)] * 8
    + [("de_DE", None)] * 6
    + [("zh_CN", None)] * 5
    + [("ja_JP", None)] * 5
    + [("es_MX", None)] * 5
    + [("en_US", "hi_IN")] * 3  # English doc + Hindi name overlay
    + [("en_US", "zh_CN")] * 2  # English doc + Chinese name overlay
)

LANG_MAP = {
    "en_US": "en",
    "en_IN": "en",
    "en_GB": "en",
    "de_DE": "de",
    "fr_FR": "fr",
    "zh_CN": "zh",
    "ja_JP": "ja",
    "es_MX": "es",
    "es_ES": "es",
    "hi_IN": "hi",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class LocaleSpec:
    primary: str
    secondary: str | None = None

    @property
    def multilingual(self) -> bool:
        return self.secondary is not None

    def lang_codes(self) -> list[str]:
        codes = [LANG_MAP.get(self.primary, "en")]
        if self.secondary:
            sec = LANG_MAP.get(self.secondary, "")
            if sec and sec not in codes:
                codes.append(sec)
        return codes


@dataclass
class DocSample:
    id: int
    text: str
    pii_gt: dict
    non_pii_data: list
    metadata: dict

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Sampling helpers
# ---------------------------------------------------------------------------


def _build_locale_pool(n: int, seed: int) -> list[LocaleSpec]:
    rng = random.Random(seed)
    pool = [LocaleSpec(p, s) for p, s in _BASE_LOCALE_SPECS]
    # Repeat and slice to fill any n > len(pool)
    while len(pool) < n:
        pool += [LocaleSpec(p, s) for p, s in _BASE_LOCALE_SPECS]
    rng.shuffle(pool)
    return pool[:n]


def _build_doc_sequence(n: int, seed: int) -> list[str]:
    rng = random.Random(seed + 1)
    types = list(REGISTRY.keys())
    repeat = (types * (n // len(types) + 1))[:n]
    rng.shuffle(repeat)
    return repeat


def _ensure_word_bounds(text: str, min_wc: int = 100, max_wc: int = 1000) -> str:
    while word_count(text) < min_wc:
        text += (
            f"\n\nThis document was generated on {fmt_date(date.today())} and is intended "
            "solely for the named recipient. Unauthorized use or distribution is prohibited. "
            "Please retain for your records.\n"
        )
    if word_count(text) > max_wc:
        lines = text.split("\n")
        while word_count("\n".join(lines)) > max_wc and len(lines) > 10:
            lines = lines[:-3]
        text = "\n".join(lines)
    return text


# ---------------------------------------------------------------------------
# Core generation
# ---------------------------------------------------------------------------


def generate_samples(n: int = 50, seed: int = 42) -> list[DocSample]:
    random.seed(seed)  # seed global random used inside templates
    locale_specs = _build_locale_pool(n, seed)
    doc_sequence = _build_doc_sequence(n, seed)
    samples: list[DocSample] = []

    for i, (doc_type, spec) in enumerate(zip(doc_sequence, locale_specs), start=1):
        fake = Faker(spec.primary)
        overlay_name = None
        if spec.multilingual and spec.secondary:
            try:
                overlay_name = Faker(spec.secondary).name()
            except Exception:
                pass

        text, pii_gt, non_pii = REGISTRY[doc_type](fake, overlay_name)
        text = _ensure_word_bounds(text)

        sample = DocSample(
            id=i,
            text=text,
            pii_gt=pii_gt,
            non_pii_data=non_pii,
            metadata={
                "type": doc_type,
                "language": spec.lang_codes(),
                "locale": spec.primary,
                "multilingual": spec.multilingual,
                "secondary_locale": spec.secondary,
                "word_count": word_count(text),
            },
        )
        samples.append(sample)
        print(
            f"[{i:2d}/{n}]  {doc_type:<22}  locale={spec.primary:<6}  "
            f"words={word_count(text):4d}  pii={len(pii_gt):2d}  non_pii={len(non_pii):2d}"
        )

    return samples


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_stats(samples: list[DocSample]) -> None:
    type_counts: dict[str, int] = {}
    for s in samples:
        t = s.metadata["type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    print("\nDoc type distribution:")
    for t, c in sorted(type_counts.items()):
        print(f"  {t:<22} {c}")

    company_traps = sum(
        1 for s in samples for e in s.non_pii_data if e["type"] == "company_name"
    )
    multilingual = sum(1 for s in samples if s.metadata["multilingual"])
    print(f"\nPerson-name company traps : {company_traps}")
    print(f"Multilingual samples      : {multilingual}")
    print(f"Registered doc types      : {sorted(REGISTRY.keys())}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic PII documents")
    parser.add_argument(
        "--output", "-o", default="samples.json", help="Output JSON path"
    )
    parser.add_argument(
        "--num-samples", "-n", type=int, default=50, help="Number of samples"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    samples = generate_samples(args.num_samples, args.seed)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump([s.to_dict() for s in samples], f, ensure_ascii=False, indent=2)

    print(f"\nWrote {len(samples)} samples → {args.output}")
    _print_stats(samples)


if __name__ == "__main__":
    main()
