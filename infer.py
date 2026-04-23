import argparse
import json
import time
import torch
from packaging.version import Version
import transformers

if Version(transformers.__version__) < Version("5.6.0"):
    raise RuntimeError(
        f"transformers>=5.6.0 required, found {transformers.__version__}.\n"
        "Run: pip install 'transformers>=5.6.0'"
    )

from transformers import AutoTokenizer, AutoModelForTokenClassification

MODEL_ID = "openai/privacy-filter"
DATASET_ID = "ai4privacy/pii-masking-200k"
NUM_SAMPLES = 30
MAX_LENGTH = 8000  # conservative; full 128k context would be slow on CPU

# Fallback samples used if HuggingFace Hub is unavailable
FALLBACK_SAMPLES = [
    "Hi, my name is John Smith and my email is john.smith@example.com.",
    "Please call me at +1-555-867-5309 or reach me at 42 Maple Street, Boston MA 02101.",
    "My account number is 4111-1111-1111-1111 and my SSN is 123-45-6789.",
    "Contact Alice Brown at alice.brown@corp.org before the meeting on March 15, 2024.",
    "The API secret key is sk-abc123xyz and should not be shared publicly.",
]


def load_model():
    print(f"Loading tokenizer from {MODEL_ID}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

    print(f"Loading model from {MODEL_ID} on CPU (bfloat16)...")
    model = AutoModelForTokenClassification.from_pretrained(
        MODEL_ID,
        dtype=torch.bfloat16,
        device_map="cpu",
    )
    model.eval()
    print(f"Model loaded. Labels: {model.config.num_labels}\n")
    return tokenizer, model


def load_samples_hf():
    try:
        from datasets import load_dataset

        print(f"Streaming {NUM_SAMPLES} samples from {DATASET_ID}...")
        ds = load_dataset(DATASET_ID, split="train", streaming=True)
        samples = [
            {"id": i + 1, "text": row["source_text"], "pii_gt": None}
            for i, row in enumerate(ds.take(NUM_SAMPLES))
        ]
        print(f"Loaded {len(samples)} samples.\n")
        return samples
    except Exception as e:
        print(f"Could not load dataset ({e}). Using fallback samples.\n")
        return [
            {"id": i + 1, "text": t, "pii_gt": None}
            for i, t in enumerate(FALLBACK_SAMPLES)
        ]


def load_samples_json(path: str):
    with open(path, encoding="utf-8") as f:
        records = json.load(f)
    print(f"Loaded {len(records)} samples from {path}\n")
    return records


def run_inference(text, tokenizer, model):
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=MAX_LENGTH,
        return_offsets_mapping=True,
    )
    offset_mapping = inputs.pop("offset_mapping")[0]  # shape [T, 2]; not a model input

    with torch.no_grad():
        outputs = model(**inputs)

    n_tokens = inputs["input_ids"].shape[1]
    label_ids = outputs.logits[0].argmax(dim=-1).tolist()
    labels = [model.config.id2label[lid] for lid in label_ids]
    return labels, offset_mapping, n_tokens


def bioes_to_spans(labels, offset_mapping):
    """Convert per-token BIOES labels to a list of character-level entity dicts."""
    spans = []
    current = None  # {"label": str, "start_tok": int}

    for i, label in enumerate(labels):
        if label == "O":
            current = None
            continue

        if "-" not in label:
            current = None
            continue

        prefix, entity_type = label.split("-", 1)

        if prefix == "S":
            current = None
            char_start = offset_mapping[i][0].item()
            char_end = offset_mapping[i][1].item()
            if char_start != char_end:  # skip special tokens with (0,0) offsets
                spans.append(
                    {"label": entity_type, "start": char_start, "end": char_end}
                )

        elif prefix == "B":
            current = {"label": entity_type, "start_tok": i}

        elif prefix == "I":
            # recover from malformed sequence
            if current is None or current["label"] != entity_type:
                current = {"label": entity_type, "start_tok": i}

        elif prefix == "E":
            if current and current["label"] == entity_type:
                char_start = offset_mapping[current["start_tok"]][0].item()
                char_end = offset_mapping[i][1].item()
                if char_start != char_end:
                    spans.append(
                        {"label": entity_type, "start": char_start, "end": char_end}
                    )
            current = None

    return spans


def mask_text(text, spans):
    """Replace entity char spans with [LABEL] placeholders (right-to-left)."""
    for span in sorted(spans, key=lambda s: s["start"], reverse=True):
        placeholder = f"[{span['label'].upper()}]"
        text = text[: span["start"]] + placeholder + text[span["end"] :]
    return text


# ---------------------------------------------------------------------------
# Benchmarking helpers
# ---------------------------------------------------------------------------


def _flatten_gt_values(pii_gt: dict) -> list[str]:
    """Extract all string PII values from pii_gt, including inside lists."""
    values = []
    for v in pii_gt.values():
        if isinstance(v, list):
            values.extend(str(x) for x in v)
        elif v is not None:
            values.append(str(v))
    return [v.strip() for v in values if v.strip()]


def _span_texts(text: str, spans: list[dict]) -> list[str]:
    return [text[s["start"] : s["end"]].strip() for s in spans]


def _is_match(pred: str, gt: str) -> bool:
    """True if pred contains or is contained by gt (case-insensitive, partial match)."""
    p, g = pred.lower(), gt.lower()
    return p in g or g in p


def benchmark_sample(
    text: str, spans: list[dict], pii_gt: dict, non_pii_data: list[dict] | None = None
) -> dict:
    """
    Compute per-sample precision, recall, F1 and non-PII false-positive rate.

    TP  — predicted span matches a pii_gt value
    FP  — predicted span matches nothing in pii_gt
      of which:
        non_pii_fp — FP span matches a non_pii_data value (known benign: admin date,
                     business address, company name that looks like a person name)
    FN  — pii_gt value not covered by any predicted span

    Matching is partial/case-insensitive (OCR text may differ slightly from gt strings).
    """
    gt_values = _flatten_gt_values(pii_gt)
    np_values = _flatten_gt_values(
        {i: v["value"] for i, v in enumerate(non_pii_data or [])}
    )
    pred_texts = _span_texts(text, spans)

    if not gt_values and not pred_texts:
        return {
            "precision": 1.0,
            "recall": 1.0,
            "f1": 1.0,
            "tp": 0,
            "fp": 0,
            "fn": 0,
            "non_pii_fp": 0,
            "addr_fp": 0,
            "date_fp": 0,
            "company_fp": 0,
        }

    tp_pred = sum(1 for p in pred_texts if any(_is_match(p, g) for g in gt_values))
    fp = len(pred_texts) - tp_pred
    recalled = sum(1 for g in gt_values if any(_is_match(p, g) for p in pred_texts))
    fn = len(gt_values) - recalled

    # Break FP spans into known-benign categories
    fp_spans = [
        s
        for s in spans
        if not any(_is_match(text[s["start"] : s["end"]], g) for g in gt_values)
    ]
    non_pii_fp = sum(
        1
        for s in fp_spans
        if any(_is_match(text[s["start"] : s["end"]], n) for n in np_values)
    )

    # Further categorise by non_pii type (date / address / company_name)
    def fp_of_type(np_type: str) -> int:
        typed = [e["value"] for e in (non_pii_data or []) if e["type"] == np_type]
        return sum(
            1
            for s in fp_spans
            if any(_is_match(text[s["start"] : s["end"]], v) for v in typed)
        )

    addr_fp = fp_of_type("address")
    date_fp = fp_of_type("date")
    company_fp = fp_of_type("company_name")

    precision = tp_pred / len(pred_texts) if pred_texts else 0.0
    recall = recalled / len(gt_values) if gt_values else 0.0
    f1 = (
        (2 * precision * recall / (precision + recall))
        if (precision + recall) > 0
        else 0.0
    )

    # Address coverage: for each pii_gt address value, check full vs partial match
    addr_coverage = []
    for key in ("address", "mailing_address", "property_address", "client_address"):
        gt_addr = pii_gt.get(key)
        if not gt_addr:
            continue
        for s in spans:
            pred = text[s["start"] : s["end"]].strip()
            if _is_match(pred, gt_addr):
                ratio = len(pred) / max(len(gt_addr), 1)
                addr_coverage.append(
                    {
                        "gt": gt_addr,
                        "predicted": pred,
                        "coverage_ratio": round(ratio, 2),
                        "full": ratio >= 0.85,
                    }
                )
                break  # first matching span per address field

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp_pred,
        "fp": fp,
        "fn": fn,
        "non_pii_fp": non_pii_fp,
        "addr_fp": addr_fp,
        "date_fp": date_fp,
        "company_fp": company_fp,
        "addr_coverage": addr_coverage,
    }


def print_benchmark_summary(all_metrics: list[dict], samples: list[dict]):
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    avg_p = sum(m["precision"] for m in all_metrics) / len(all_metrics)
    avg_r = sum(m["recall"] for m in all_metrics) / len(all_metrics)
    avg_f1 = sum(m["f1"] for m in all_metrics) / len(all_metrics)
    total_tp = sum(m["tp"] for m in all_metrics)
    total_fp = sum(m["fp"] for m in all_metrics)
    total_fn = sum(m["fn"] for m in all_metrics)

    total_non_pii_fp = sum(m.get("non_pii_fp", 0) for m in all_metrics)
    total_date_fp = sum(m.get("date_fp", 0) for m in all_metrics)
    total_addr_fp = sum(m.get("addr_fp", 0) for m in all_metrics)
    total_company_fp = sum(m.get("company_fp", 0) for m in all_metrics)

    print(f"Samples evaluated     : {len(all_metrics)}")
    print(f"Avg Precision         : {avg_p:.3f}")
    print(f"Avg Recall            : {avg_r:.3f}")
    print(f"Avg F1                : {avg_f1:.3f}")
    print(f"Total TP / FP / FN    : {total_tp} / {total_fp} / {total_fn}")
    print()
    print(f"False positives on known-benign values: {total_non_pii_fp}")
    print(f"  Admin dates flagged as private_date  : {total_date_fp}")
    print(f"  Business addresses flagged           : {total_addr_fp}")
    print(f"  Company names flagged as person      : {total_company_fp}")

    # Address coverage (full vs partial)
    all_addr = [a for m in all_metrics for a in m.get("addr_coverage", [])]
    if all_addr:
        full = sum(1 for a in all_addr if a["full"])
        partial = len(all_addr) - full
        avg_cov = sum(a["coverage_ratio"] for a in all_addr) / len(all_addr)
        print(f"\nAddress masking  (n={len(all_addr)} matched addresses)")
        print(f"  Full address masked   : {full}  ({full / len(all_addr) * 100:.0f}%)")
        print(
            f"  Partial mask          : {partial}  ({partial / len(all_addr) * 100:.0f}%)"
        )
        print(
            f"  Avg coverage ratio    : {avg_cov:.2f}  (1.0 = exact span, <1 = partial)"
        )
        if partial:
            print("  Partial examples:")
            for a in [x for x in all_addr if not x["full"]][:3]:
                print(f"    GT:   {a['gt'][:60]}")
                print(f"    Pred: {a['predicted'][:60]}  (ratio={a['coverage_ratio']})")

    # Per doc-type
    type_metrics: dict[str, list] = {}
    for s, m in zip(samples, all_metrics):
        t = s.get("metadata", {}).get("type", "unknown")
        type_metrics.setdefault(t, []).append(m)
    if len(type_metrics) > 1:
        print("\nPer-type F1 / company-FP:")
        for t, ms in sorted(type_metrics.items()):
            f1 = sum(m["f1"] for m in ms) / len(ms)
            cfp = sum(m.get("company_fp", 0) for m in ms)
            print(f"  {t:<22} n={len(ms):2d}  F1={f1:.3f}  company_fp={cfp}")

    # Per-locale
    locale_metrics: dict[str, list] = {}
    for s, m in zip(samples, all_metrics):
        loc = s.get("metadata", {}).get("locale", "unknown")
        locale_metrics.setdefault(loc, []).append(m)
    if len(locale_metrics) > 1:
        print("\nPer-locale F1:")
        for loc, ms in sorted(locale_metrics.items()):
            f1 = sum(m["f1"] for m in ms) / len(ms)
            print(f"  {loc:<10} n={len(ms):2d}  F1={f1:.3f}")


def print_latency_summary(all_latencies: list[dict]):
    if not all_latencies:
        return
    print("\n" + "=" * 60)
    print("LATENCY SUMMARY")
    print("=" * 60)

    lats = sorted(m["latency_ms"] for m in all_latencies)
    tokens = [m["n_tokens"] for m in all_latencies]
    n = len(lats)

    def percentile(sorted_list, p):
        idx = max(0, int(p / 100 * n) - 1)
        return sorted_list[min(idx, n - 1)]

    total_ms = sum(lats)
    total_tok = sum(tokens)
    avg_lat = total_ms / n
    throughput = total_tok / (total_ms / 1000) if total_ms > 0 else 0

    print(f"Samples          : {n}")
    print(f"Min latency      : {lats[0]:.0f} ms")
    print(f"P50 latency      : {percentile(lats, 50):.0f} ms")
    print(f"P95 latency      : {percentile(lats, 95):.0f} ms")
    print(f"Max latency      : {lats[-1]:.0f} ms")
    print(f"Avg latency      : {avg_lat:.0f} ms")
    print(f"Total wall time  : {total_ms / 1000:.1f} s")
    print(f"Avg tokens/sample: {total_tok / n:.0f}")
    print(f"Throughput       : {throughput:.0f} tokens/sec")

    # Per doc-type latency
    type_lat: dict[str, list] = {}
    for m in all_latencies:
        type_lat.setdefault(m.get("doc_type", "unknown"), []).append(m["latency_ms"])
    if len(type_lat) > 1:
        print("\nPer-type avg latency:")
        for t, lats_t in sorted(type_lat.items()):
            print(f"  {t:<22} avg={sum(lats_t) / len(lats_t):.0f} ms  n={len(lats_t)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Run openai/privacy-filter inference")
    parser.add_argument(
        "--input",
        "-i",
        default=None,
        help="Path to samples.json (output of generate_samples.py). "
        "If omitted, streams from HuggingFace ai4privacy dataset.",
    )
    parser.add_argument(
        "--benchmark",
        "-b",
        action="store_true",
        help="Compute precision/recall/F1 against pii_gt (requires --input)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress per-sample text output (still shows metrics)",
    )
    args = parser.parse_args()

    tokenizer, model = load_model()

    if args.input:
        samples = load_samples_json(args.input)
    else:
        samples = load_samples_hf()

    all_metrics = []
    all_latencies = []

    for sample in samples:
        sid = sample.get("id", "?")
        text = sample["text"]
        pii_gt = sample.get("pii_gt")
        doc_type = sample.get("metadata", {}).get("type", "")
        locale = sample.get("metadata", {}).get("locale", "")

        if not args.quiet:
            print(f"\n{'=' * 60}")
            label = f"Sample {sid}"
            if doc_type:
                label += f"  [{doc_type}]"
            if locale:
                label += f"  locale={locale}"
            print(label)
            print(f"\nORIGINAL:\n{text}")

        t0 = time.perf_counter()
        labels, offset_mapping, n_tokens = run_inference(text, tokenizer, model)
        latency_ms = (time.perf_counter() - t0) * 1000

        spans = bioes_to_spans(labels, offset_mapping)
        masked = mask_text(text, spans)

        all_latencies.append(
            {
                "latency_ms": latency_ms,
                "n_tokens": n_tokens,
                "doc_type": doc_type,
            }
        )

        if not args.quiet:
            if spans:
                print(f"\nDETECTED PII ({len(spans)} entities):")
                for span in sorted(spans, key=lambda s: s["start"]):
                    entity_text = text[span["start"] : span["end"]]
                    print(
                        f"  [{span['label']}] '{entity_text}'  (chars {span['start']}–{span['end']})"
                    )
            else:
                print("\nDETECTED PII: none")

            print(f"\nMASKED:\n{masked}")
            print(f"\nLatency: {latency_ms:.0f} ms  ({n_tokens} tokens)")

        if args.benchmark and pii_gt:
            non_pii_data = sample.get("non_pii_data") or []
            m = benchmark_sample(text, spans, pii_gt, non_pii_data)
            all_metrics.append(m)
            if not args.quiet:
                print(
                    f"Metrics  P={m['precision']:.2f}  R={m['recall']:.2f}  F1={m['f1']:.2f}  "
                    f"TP={m['tp']} FP={m['fp']} FN={m['fn']}  "
                    f"[non-PII FP: dates={m['date_fp']} addr={m['addr_fp']} company={m['company_fp']}]"
                )

    print(f"\nDone. Processed {len(samples)} samples.")

    print_latency_summary(all_latencies)

    if args.benchmark and all_metrics:
        print_benchmark_summary(all_metrics, samples)


if __name__ == "__main__":
    main()
