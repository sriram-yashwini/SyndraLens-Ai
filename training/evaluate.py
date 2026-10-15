
"""
Evaluate a system on the gold test set and handwritten challenge set.

Usage:
    python scripts/04_evaluate.py --system rule
    python scripts/04_evaluate.py --system slm --limit 30 --challenge-limit 16

Writes:
    outputs/eval_<system>.json
    outputs/errors_<system>.jsonl
"""

import argparse
import json
import os
import sys
import time

ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from _boot import load_config
from syndralens.challenge import CHALLENGE
from syndralens.inference import load_backend
from syndralens.schema import (
    infer_exposures,
    new_symptom,
    parse_model_output,
    serialize_target,
)


def prf(tp, fp, fn):
    if tp + fp + fn == 0:
        return {
            "precision": None,
            "recall": None,
            "f1": None,
        }

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


class Acc:
    def __init__(self):
        self.tp = 0
        self.fp = 0
        self.fn = 0

    def add(self, gold, pred):
        self.tp += len(gold & pred)
        self.fp += len(pred - gold)
        self.fn += len(gold - pred)

    def out(self):
        return prf(self.tp, self.fp, self.fn)


def sym_keys(symptoms, fields):
    return {
        tuple(symptom.get(field) for field in fields)
        for symptom in symptoms
    }


def evaluate(backend, rows, name, err_file=None):
    strict = Acc()
    names = Acc()
    expo = Acc()
    syn = Acc()

    slm_only_strict = Acc()
    slm_only_names = Acc()

    attr = {
        "severity": [0, 0],
        "trend": [0, 0],
        "duration": [0, 0],
    }

    field = {
        "assertion": [0, 0],
        "time": [0, 0],
        "who": [0, 0],
    }

    raw_valid_count = 0
    repaired_count = 0
    fallback_count = 0
    salvaged_count = 0
    viol_count = 0
    scored = 0

    strict_fields = ("name", "assertion", "who", "time")

    for i, row in enumerate(rows):
        t0 = time.time()

        gold, ok = parse_model_output(row["target"])

        if not ok:
            print(
                f"[{name}] skipping row {i}: gold target invalid",
                flush=True,
            )
            continue

        scored += 1
        result = backend.extract(row["text"])

        is_fallback = result.get("fallback_used", False)

        is_raw_valid = result.get(
            "raw_model_output_valid",
            result.get("valid_json", False),
        )

        if is_raw_valid:
            raw_valid_count += 1

        if result.get("model_output_repaired", False):
            repaired_count += 1

        if is_fallback:
            fallback_count += 1

        if result.get("items_dropped"):
            salvaged_count += 1

        viol_count += len(
            result.get("guardrail_violations", [])
        )

        pred_symptoms = result["symptoms"]
        gold_symptoms = gold["symptoms"]

        pred_strict = sym_keys(pred_symptoms, strict_fields)
        gold_strict = sym_keys(gold_symptoms, strict_fields)

        pred_names = sym_keys(pred_symptoms, ("name",))
        gold_names = sym_keys(gold_symptoms, ("name",))

        strict.add(gold_strict, pred_strict)
        names.add(gold_names, pred_names)

        # Apply the same exposure inference to gold and prediction.
        gold_exposures = infer_exposures(
            gold_symptoms,
            gold["exposures"],
        )

        expo.add(
            sym_keys(gold_exposures, ("type", "assertion")),
            sym_keys(result["exposures"], ("type", "assertion")),
        )

        syn.add(
            {
                (s["syndrome"], s["signal"])
                for s in gold["syndromes"]
            },
            {
                (s["syndrome"], s["signal"])
                for s in result["syndromes"]
            },
        )

        # Metrics for outputs that did not use fallback.
        if not is_fallback:
            slm_only_strict.add(gold_strict, pred_strict)
            slm_only_names.add(gold_names, pred_names)

        # Attribute accuracy: match the complete strict symptom key.
        pred_by_strict = {
            tuple(symptom.get(f) for f in strict_fields): symptom
            for symptom in pred_symptoms
        }

        for gold_symptom in gold_symptoms:
            if gold_symptom.get("assertion") != "present":
                continue

            key = tuple(
                gold_symptom.get(f) for f in strict_fields
            )
            pred_symptom = pred_by_strict.get(key)

            if pred_symptom is not None:
                for attribute in attr:
                    attr[attribute][1] += 1
                    attr[attribute][0] += int(
                        pred_symptom.get(attribute)
                        == gold_symptom.get(attribute)
                    )

        # Assertion, time and who accuracy, conditional on name match.
        pred_by_name = {}

        for symptom in pred_symptoms:
            pred_by_name.setdefault(symptom.get("name"), symptom)

        for gold_symptom in gold_symptoms:
            pred_symptom = pred_by_name.get(
                gold_symptom.get("name")
            )

            if pred_symptom is not None:
                for field_name in field:
                    field[field_name][1] += 1
                    field[field_name][0] += int(
                        pred_symptom.get(field_name)
                        == gold_symptom.get(field_name)
                    )

        # Write strict symptom mismatches for later inspection.
        if err_file is not None and gold_strict != pred_strict:
            err_file.write(
                json.dumps(
                    {
                        "set": name,
                        "text": row["text"],
                        "fallback": is_fallback,
                        "missing": sorted(
                            map(list, gold_strict - pred_strict)
                        ),
                        "extra": sorted(
                            map(list, pred_strict - gold_strict)
                        ),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

        print(
            f"[{name}] {i + 1}/{len(rows)} "
            f"{time.time() - t0:.1f}s",
            flush=True,
        )

    denominator = max(1, scored)

    return {
        "set": name,
        "n": scored,
        "raw_json_valid_rate": round(
            raw_valid_count / denominator, 4
        ),
        "repaired_rate": round(
            repaired_count / denominator, 4
        ),
        "salvaged_rate": round(
            salvaged_count / denominator, 4
        ),
        "fallback_rate": round(
            fallback_count / denominator, 4
        ),
        "guardrail_violations": viol_count,
        "symptom_strict": strict.out(),
        "symptom_name_only": names.out(),
        "slm_pure_symptom_strict": slm_only_strict.out(),
        "slm_pure_symptom_name_only": slm_only_names.out(),
        "field_accuracy_given_name_match": {
            field_name: (
                round(correct / total, 4) if total else None
            )
            for field_name, (correct, total) in field.items()
        },
        "exposure": expo.out(),
        "syndrome": syn.out(),
        "attribute_accuracy": {
            attribute: (
                round(correct / total, 4) if total else None
            )
            for attribute, (correct, total) in attr.items()
        },
    }


def challenge_rows():
    rows = []

    for text, keys in CHALLENGE:
        symptoms = [
            new_symptom(name, assertion, symptom_time, who)
            for name, assertion, who, symptom_time in keys
        ]

        rows.append(
            {
                "text": text,
                "target": serialize_target(
                    symptoms, [], []
                ),
            }
        )

    return rows


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--system",
        choices=["rule", "slm"],
        default="rule",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of gold test rows",
    )
    parser.add_argument(
        "--challenge-limit",
        type=int,
        default=None,
        help="Maximum number of challenge rows",
    )
    parser.add_argument(
        "--skip-challenge",
        action="store_true",
    )

    args = parser.parse_args()

    if args.limit is not None and args.limit < 0:
        parser.error("--limit must be zero or greater")

    if (
        args.challenge_limit is not None
        and args.challenge_limit < 0
    ):
        parser.error("--challenge-limit must be zero or greater")

    cfg = load_config()
    backend = load_backend(args.system, cfg)

    test_path = os.path.join(
        ROOT,
        cfg["data"]["processed_dir"],
        "test.jsonl",
    )

    if not os.path.isfile(test_path):
        raise FileNotFoundError(
            f"Test dataset not found: {test_path}"
        )

    with open(test_path, encoding="utf-8") as file:
        test = [
            json.loads(line)
            for line in file
            if line.strip()
        ]

    if args.limit is not None:
        test = test[:args.limit]

    if not test:
        raise ValueError(
            "The gold test set is empty. Check the dataset path and limit."
        )

    output_dir = os.path.join(ROOT, "outputs")
    os.makedirs(output_dir, exist_ok=True)

    errors_path = os.path.join(
        output_dir,
        f"errors_{args.system}.jsonl",
    )

    out_path = os.path.join(
        output_dir,
        f"eval_{args.system}.json",
    )

    results = []

    with open(errors_path, "w", encoding="utf-8") as err_file:
        results.append(
            evaluate(backend, test, "gold_test", err_file)
        )

        if not args.skip_challenge:
            rows = challenge_rows()

            if args.challenge_limit is not None:
                rows = rows[:args.challenge_limit]

            if rows:
                challenge_result = evaluate(
                    backend,
                    rows,
                    "challenge",
                    err_file,
                )

                # Challenge labels do not contain gold exposure
                # or syndrome annotations; do not report those metrics.
                for key in (
                    "exposure",
                    "syndrome",
                    "attribute_accuracy",
                ):
                    challenge_result.pop(key, None)

                results.append(challenge_result)
            else:
                print(
                    "Challenge set is empty after applying the limit.",
                    flush=True,
                )

    with open(out_path, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)

    print("\nEvaluation results:")
    print(json.dumps(results, indent=2))
    print(f"\nResults saved to: {out_path}")
    print(f"Strict mismatch details saved to: {errors_path}")


if __name__ == "__main__":
    main()
