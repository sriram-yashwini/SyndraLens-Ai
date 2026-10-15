
import collections
import hashlib
import json
import os
import random
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
for p in (SCRIPT_DIR, PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

FAILS, WARNS = [], []


def ok(msg):
    print("  OK   ", msg)


def warn(msg):
    WARNS.append(msg)
    print("  WARN ", msg)


def fail(msg):
    FAILS.append(msg)
    print("  FAIL ", msg)


def head(msg):
    print("\n== " + msg)


def finish():
    print("\n" + "=" * 60)
    print(f"{len(FAILS)} FAIL, {len(WARNS)} WARN")
    for f in FAILS:
        print("  FAIL:", f)
    sys.exit(1 if FAILS else 0)


# ------------------------------------------------------------ 1. packages
head("1. Package versions")
from importlib.metadata import PackageNotFoundError, version

for pkg in ("torch", "transformers", "peft", "datasets", "accelerate", "pyyaml"):
    try:
        print(f"  {pkg:13} {version(pkg)}")
    except PackageNotFoundError:
        fail(f"{pkg} is not installed")
try:
    major, minor = (int(x) for x in version("transformers").split(".")[:2])
    if (major, minor) < (4, 56):
        fail("transformers < 4.56: `dtype=` is not supported; upgrade transformers")
    else:
        ok("transformers supports dtype=")
except Exception:
    warn("could not parse transformers version")

# ------------------------------------------------------------ 2. ontology
head("2. Ontology and schema")
from training._boot import load_config

cfg = load_config()
try:
    from syndralens import ontology as O
    from syndralens import schema as S
except Exception as e:
    fail(f"cannot import syndralens.ontology / schema: {type(e).__name__}: {e}")
    finish()

for need in ("_labels", "_FORMAT_EXAMPLE", "parse_model_output_ex", "SYMPTOM_ALIASES"):
    if not hasattr(S, need):
        fail(f"schema.py lacks {need}: it is not the corrected version")
if FAILS:
    finish()

SYMS, SYNS = set(O.SYMPTOMS), set(O.SYNDROMES)
for name in ("SYMPTOMS", "ASSERTIONS", "TIMES", "WHO", "SEVERITIES", "TRENDS",
             "EXPOSURES", "EXPOSURE_ASSERTIONS", "SYNDROMES", "SIGNAL_LEVELS"):
    vals = getattr(O, name)
    shown = list(vals) if isinstance(vals, (list, tuple)) else sorted(vals)
    print(f"  {name} ({len(shown)}): {shown}")

required = {
    "ASSERTIONS": {"present", "absent", "possible", "hypothetical"},
    "TIMES": {"current", "past", "chronic"},
    "WHO": {"patient", "family", "other"},
    "SEVERITIES": {"mild", "moderate", "severe", "unspecified"},
    "TRENDS": {"worsening", "improving", "stable", "unknown"},
    "EXPOSURE_ASSERTIONS": {"present", "absent", "possible"},
}
for attr, need in required.items():
    missing = need - set(getattr(O, attr))
    if missing:
        fail(f"{attr} lacks {sorted(missing)} (the generator assumes them)")
    else:
        ok(f"{attr} contains {sorted(need)}")

overlap = SYMS & SYNS
if overlap:
    fail(f"names in BOTH symptoms and syndromes: {sorted(overlap)}")
else:
    ok("no overlap between symptom names and syndrome names")

for alias, target in S.SYMPTOM_ALIASES.items():
    if target not in SYMS:
        warn(f"alias {alias!r} -> {target!r}, but {target!r} is not a symptom")
    if alias in SYMS:
        warn(f"alias {alias!r} is also a real symptom label and shadows it")

owners = collections.defaultdict(set)
for sname, spec in O.SYMPTOMS.items():
    for key in ("formal", "colloquial", "abbr"):
        for ph in spec.get(key, []):
            owners[ph.lower()].add(sname)
ambiguous = {ph: sorted(n) for ph, n in owners.items() if len(n) > 1}
print(f"  neck_pain in SYMPTOMS: {'neck_pain' in SYMS}")
if ambiguous:
    warn(f"phrases that belong to more than one symptom: {ambiguous}")
else:
    ok("no ambiguous phrases in the lexicon")

# ------------------------------------------------------------ 3. prompt
head("3. Prompt")
try:
    json.loads(S._FORMAT_EXAMPLE)
    ok("format example is valid JSON")
except ValueError as e:
    fail(f"format example is not valid JSON: {e}")
_, ex_valid = S.parse_model_output(S._FORMAT_EXAMPLE)
if ex_valid:
    ok("format example passes strict schema validation")
else:
    fail("format example fails strict validation")
if S._FORMAT_EXAMPLE not in S.TASK_INSTRUCTION:
    fail("TASK_INSTRUCTION does not contain the format example")

max_len = int(cfg["model"].get("max_seq_len", 768))
tok = None
try:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(cfg["model"]["base_model"])
    n = len(tok(S.TASK_INSTRUCTION)["input_ids"])
    print(f"  system prompt tokens: {n} (max_seq_len={max_len})")
    if n > 0.6 * max_len:
        warn("prompt uses over 60% of max_seq_len; long examples will be dropped")
    else:
        ok("prompt leaves room for the text and answer")
except Exception as e:
    warn(f"tokenizer unavailable ({type(e).__name__}); token-length checks skipped")


def example_len(row):
    prompt = tok.apply_chat_template(
        [
            {"role": "system", "content": S.TASK_INSTRUCTION},
            {"role": "user", "content": (
                f"Clinical text (extract only supported facts):\n{row['text']}\n"
                "Return exactly one complete JSON object. Do not omit required fields.")},
        ],
        tokenize=False, add_generation_prompt=True,
    )
    return (len(tok(prompt, add_special_tokens=False)["input_ids"])
            + len(tok(row["target"] + "<|im_end|>", add_special_tokens=False)["input_ids"]))


# ------------------------------------------------------------ 4. data
head("4. Datasets")
from syndralens.challenge import CHALLENGE

challenge_texts = {t.strip().lower() for t, _ in CHALLENGE}


def toks(t):
    return set(re.findall(r"\w+", t.lower()))


challenge_toks = [toks(t) for t, _ in CHALLENGE]


def read(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


dirs = []
for d in ("data/processed_v2", cfg["data"]["processed_dir"], "data/processed_v3"):
    d = os.path.normpath(d)
    if d not in dirs:
        dirs.append(d)

combos = {}
for d in dirs:
    if not os.path.exists(os.path.join(d, "train.jsonl")):
        print(f"\n  [{d}] not built yet, skipped")
        continue
    print(f"\n  [{d}]")
    splits = {s: read(os.path.join(d, f"{s}.jsonl"))
              for s in ("train", "val", "test") if os.path.exists(os.path.join(d, f"{s}.jsonl"))}
    for s, rows in splits.items():
        bad = sum(1 for r in rows if not S.parse_model_output(r["target"])[1])
        empty = sum(1 for r in rows if r["target"].startswith('{"symptoms":[]'))
        print(f"    {s}: {len(rows)} rows, {empty} with no symptoms")
        if bad:
            fail(f"{d}/{s}: {bad} targets fail strict validation")
        if tok is not None and rows:
            lens = [example_len(r) for r in rows]
            over = sum(1 for x in lens if x > max_len)
            print(f"    {s}: tokens max={max(lens)} mean={sum(lens)/len(lens):.0f} over {max_len}: {over}")
            if over > max(2, 0.02 * len(rows)):
                fail(f"{d}/{s}: {over} rows exceed max_seq_len; raise it or shorten the prompt")
            elif over:
                warn(f"{d}/{s}: {over} rows exceed max_seq_len and will be dropped")
    tr = {r["text"].strip().lower() for r in splits["train"]}
    for other in ("val", "test"):
        if other in splits:
            leak = tr & {r["text"].strip().lower() for r in splits[other]}
            if leak:
                fail(f"{d}: {len(leak)} texts appear in both train and {other}")
    cl = tr & challenge_texts
    if cl:
        fail(f"{d}: {len(cl)} challenge texts are inside train (the challenge set must stay unseen)")
    near = 0
    for r in splits["train"]:
        tt = toks(r["text"])
        if tt and any(ct and len(tt & ct) / len(tt | ct) >= 0.8 for ct in challenge_toks):
            near += 1
    if near:
        warn(f"{d}: {near} train rows are near-duplicates (>=80% word overlap) of challenge texts")
    c = collections.Counter()
    for r in splits["train"]:
        obj, valid = S.parse_model_output(r["target"])
        if valid:
            for s in obj["symptoms"]:
                c[(s["assertion"], s["time"], s["who"])] += 1
    combos[d] = c

if combos:
    print("\n  (assertion, time, who) counts in train:")
    keys = sorted({k for c in combos.values() for k in c})
    print("  " + " " * 44 + "".join(f"{d.split(os.sep)[-1][-14:]:>16}" for d in combos))
    for k in keys:
        print("  " + f"{str(k):44}" + "".join(f"{combos[d][k]:16}" for d in combos))
    base = combos.get(os.path.normpath("data/processed_v2"))
    if base is not None:
        for d, c in combos.items():
            for k in c:
                if base[k] == 0:
                    warn(f"{d}: combination {k} never appears in the ORIGINAL data; check the convention")

orig = os.path.normpath("data/processed_v2/train.jsonl")
if os.path.exists(orig):
    rows = read(orig)

    with_, without = 0, 0
    for r in rows:
        obj, valid = S.parse_model_output(r["target"])
        if not valid:
            continue
        implied = any(s["who"] in ("family", "other") and s["assertion"] == "present"
                      and s["time"] == "current" for s in obj["symptoms"])
        if implied:
            if any(e["type"] == "sick_contact" for e in obj["exposures"]):
                with_ += 1
            else:
                without += 1
    print(f"\n  Original rows with a present family/other symptom: "
          f"{with_} have sick_contact in the target, {without} do not")
    if with_ and without and min(with_, without) / (with_ + without) > 0.2:
        warn("original data is MIXED on inferred sick_contact; the generator will refuse to guess")

    if ambiguous:
        print("\n  Ambiguous phrases in the ORIGINAL data and the labels they received:")
        for ph, own in ambiguous.items():
            rx = re.compile(r"(?<!\w)" + re.escape(ph) + r"(?!\w)", re.I)
            hits = [r for r in rows if rx.search(r["text"])]
            if not hits:
                continue
            c = collections.Counter()
            for r in hits:
                obj, valid = S.parse_model_output(r["target"])
                if valid:
                    for s in obj["symptoms"]:
                        if s["name"] in own:
                            c[s["name"]] += 1
            print(f"   '{ph}': {len(hits)} rows, labels {dict(c)}")
            if len(c) > 1:
                warn(f"'{ph}' is labeled inconsistently in the original data: {dict(c)}")

    print("\n  Original examples with absent/possible/hypothetical/past/chronic/family/other:")
    random.Random(1).shuffle(rows)
    shown = 0
    for r in rows:
        obj, valid = S.parse_model_output(r["target"])
        if valid and any(s["assertion"] != "present" or s["time"] != "current" or s["who"] != "patient"
                         for s in obj["symptoms"]):
            print("   -", r["text"])
            print("    ", r["target"][:260])
            shown += 1
            if shown == 6:
                break

# ------------------------------------------------------------ 5. originals
head("5. Originals and adapters")
for path in ("data/processed_v2/train.jsonl", "data/processed_v2/val.jsonl", "data/processed_v2/test.jsonl"):
    if os.path.exists(path):
        h = hashlib.sha256(open(path, "rb").read()).hexdigest()[:12]
        print(f"  {path}  sha256={h}   (rerun later; it must not change)")
old_adapter = os.path.normpath("models/syndralens-lora-v3")
new_adapter = os.path.normpath(cfg["model"]["adapter_dir"])
if new_adapter == old_adapter:
    fail("config adapter_dir points at the OLD adapter; training would overwrite it")
elif os.path.isdir(old_adapter):
    ok(f"old adapter {old_adapter} exists and is separate from {new_adapter}")
else:
    warn(f"old adapter {old_adapter} not found")
if os.path.isdir(new_adapter) and os.listdir(new_adapter):
    warn(f"{new_adapter} already contains files (earlier partial run?); delete it to start clean")

finish()
