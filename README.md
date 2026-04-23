# openai-privacy-filter

Benchmark and inference harness for [openai/privacy-filter](https://huggingface.co/openai/privacy-filter), OpenAI's open-source PII detection model.

Runs fully on CPU. Includes a synthetic document generator with ground-truth labels so you can measure precision, recall, and false-positive rates out of the box.

---

## Model

| Property | Detail |
|---|---|
| Architecture | Token classification (NER), BIOES tagging |
| Parameters | 1.5 B total / **50 M active** (sparse MoE, top-4 routing) |
| Context window | 128 k tokens |
| CPU inference | Yes — designed for on-device deployment |
| RAM (bfloat16) | ~1.4 GB |
| Speed | ~2–5 s / 512 tokens on a modern laptop CPU |
| License | Apache 2.0 |

**PII categories detected:** `account_number` · `private_address` · `private_email` · `private_person` · `private_phone` · `private_url` · `private_date` · `secret`

---

## Project layout

```
openai-privacy-filter/
├── infer.py                  # Inference + benchmark runner
├── generate_samples.py       # Synthetic document generator
├── requirements.txt          # Python dependencies
├── templates/
│   ├── __init__.py           # Auto-discovers generators from sibling modules
│   ├── base.py               # Shared helpers, constants, non-PII factories
│   ├── w2.py                 # W-2 Wage & Tax Statement
│   ├── form_1099.py          # Form 1099 (NEC / MISC / INT / DIV)
│   ├── bank_statement.py     # Bank account statement
│   ├── paystub.py            # Employee pay stub
│   ├── invoice.py            # Vendor invoice
│   ├── mortgage_insurance.py # Homeowners insurance declarations
│   └── auto_insurance.py     # Automobile insurance declarations
└── samples.json              # Generated benchmark dataset (after running generator)
```

---

## Setup

Requires Python 3.12+ and `transformers >= 5.6.0` (the custom model architecture is not registered in earlier versions).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

> **Note:** If you have `transformers < 5.6.0` globally installed (the system default is 4.x), the venv isolates this upgrade so nothing else is affected.

---

## Quickstart

### 1. Generate benchmark data

```bash
python generate_samples.py
```

Produces `samples.json` — 50 synthetic OCR-style documents across 7 document types and 6 locales, with:
- `pii_gt` — ground-truth PII values the model **should** flag
- `non_pii_data` — known-benign values the model **should not** flag (admin dates, business addresses, person-name-looking company names)

Options:

```bash
python generate_samples.py --num-samples 100 --seed 7 --output my_data.json
```

### 2. Run inference

```bash
# On generated data (first run downloads the 2.8 GB model weights)
python infer.py --input samples.json

# Stream 30 samples live from HuggingFace ai4privacy/pii-masking-200k
python infer.py
```

### 3. Benchmark against ground truth

```bash
python infer.py --input samples.json --benchmark

# Suppress per-sample text, show summary only
python infer.py --input samples.json --benchmark --quiet
```

Full results on 100 samples: **[RESULTS.md](RESULTS.md)**

Key numbers at a glance (100 samples, CPU, bfloat16):

| Metric | Value |
|---|---|
| Avg F1 | 0.587 |
| Avg Precision | 0.619 |
| Avg Recall | 0.627 |
| P50 latency | 1033 ms |
| Throughput | 363 tokens/sec |
| Best doc type | auto_insurance (F1 0.854) |
| Worst doc type | w2 (F1 0.382) |
| Address fully masked | 66% |

The largest source of false positives is admin dates (invoice dates, pay periods, transaction dates) being tagged as `private_date` — 44.5% of all FPs. See [RESULTS.md](RESULTS.md) for the full breakdown and observations.

---

## Benchmark design

### Ground truth (`pii_gt`)

Values the model is expected to detect — personal PII only:

| Field | Examples |
|---|---|
| Name | Employee, insured, client, agent names |
| Address | Personal home / mailing / property addresses |
| Phone / Email | Personal contact info |
| SSN / EIN | Social Security and Employer Identification numbers |
| Date of birth | Only DOB — not administrative dates |
| Account / routing | Bank account and routing numbers |
| Driver license | License number |
| VIN / plate | Vehicle identifiers |
| Policy / loan number | Insurance and mortgage identifiers |

### Known-benign values (`non_pii_data`)

Values that should **not** be flagged. False positives against these are broken out separately in the benchmark:

| Type | Reason not PII |
|---|---|
| `date` — invoice date, pay date, policy period, statement dates, transaction dates | Administrative / operational, not identity-revealing |
| `address` — employer, vendor, insurer, bank addresses | Business addresses, publicly available |
| `company_name` — e.g. `"Williams Insurance Co."` | Company names that visually resemble person names; ~60 % of generated company fields use this pattern to stress-test false positive rate |

### Date PII vs. non-PII

The model's `private_date` category is intended for **date of birth** and other personally identifying dates (hire date, medical dates). Administrative dates on documents — invoice dates, pay periods, policy effective dates, transaction dates — should not be flagged. The benchmark tracks over-flagging of these separately as `date_fp`.

---

## Adding a new document type

Create `templates/<name>.py` with two things:

```python
# templates/health_eob.py
DOC_TYPE = "health_eob"

def generate(fake, overlay_name=None):
    ...
    return text, pii_gt, non_pii_data
```

That's it — `templates/__init__.py` auto-discovers any module that exports `DOC_TYPE` and `generate()`. No registration needed elsewhere.

See `templates/base.py` for shared helpers (`ocr_space`, `money`, `fmt_date`, `pad`, `non_pii_date`, `non_pii_addr`, `non_pii_company`, `person_company`, etc.).

---

## Locales and multilingual samples

The generator covers 6 locale groups by default. 5 of the 50 samples are multilingual — an English-language document where a person's name is shown in both English and a native script (Hindi Devanagari or Chinese characters), simulating bilingual OCR output.

| Locale | Count | Notes |
|---|---|---|
| `en_US` | 16 | American English |
| `en_IN` | 8 | Indian English |
| `de_DE` | 6 | German |
| `zh_CN` | 5 | Chinese (Simplified) |
| `ja_JP` | 5 | Japanese |
| `es_MX` | 5 | Spanish (Mexico) |
| `en_US` + `hi_IN` overlay | 3 | Multilingual: name shown in English + Devanagari |
| `en_US` + `zh_CN` overlay | 2 | Multilingual: name shown in English + Chinese characters |

---

## Dependencies

| Package | Purpose |
|---|---|
| `transformers >= 5.6.0` | Model loading and inference (5.6+ required for custom architecture) |
| `torch >= 2.4.0` | PyTorch backend (CPU only) |
| `faker >= 26.0.0` | Synthetic PII generation |
| `datasets >= 3.0.0` | Stream HuggingFace datasets |
| `safetensors >= 0.4.0` | Load model weights (2.8 GB `.safetensors` file) |
| `huggingface-hub >= 0.27.0` | Model and dataset downloads |
| `packaging >= 23.0` | Runtime version check |

---

## References

- [openai/privacy-filter on HuggingFace](https://huggingface.co/openai/privacy-filter)
- [Introducing OpenAI Privacy Filter](https://openai.com/index/introducing-openai-privacy-filter/)
- [ai4privacy/pii-masking-200k dataset](https://huggingface.co/datasets/ai4privacy/pii-masking-200k)
