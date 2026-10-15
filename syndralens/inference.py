
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

from . import rule_extractor
from .ontology import DISCLAIMER, SYMPTOMS, WHO
from .schema import (
    TASK_INSTRUCTION,
    guardrail_violations,
    infer_exposures,
    parse_model_output_ex,
)
from .syndrome_engine import compute_syndromes, interpret


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_project_path(path: str) -> str:
    """Resolve relative model paths from the project root."""
    candidate = Path(path).expanduser()

    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate

    return str(candidate.resolve())


def _syndrome_pairs(syndromes) -> set:
    """Convert syndrome records into comparable name/signal pairs."""
    if not isinstance(syndromes, list):
        return set()

    pairs = set()

    for item in syndromes:
        if not isinstance(item, dict):
            continue

        name = item.get("syndrome")
        signal = item.get("signal")

        if isinstance(name, str) and isinstance(signal, str):
            pairs.add((name, signal))

    return pairs


def finalize(
    symptoms,
    exposures,
    model_syndromes=None,
    backend="slm",
    valid_json=True,
    fallback=False,
    raw_text=None,
) -> Dict[str, Any]:
    """Build the final result using deterministic syndrome reasoning."""

    symptoms = symptoms if isinstance(symptoms, list) else []
    exposures = exposures if isinstance(exposures, list) else []

    exposures = infer_exposures(symptoms, exposures)

    engine_syndromes = compute_syndromes(symptoms)

    consistent = (
        model_syndromes is None
        or _syndrome_pairs(model_syndromes)
        == _syndrome_pairs(engine_syndromes)
    )

    result = {
        "symptoms": symptoms,
        "exposures": exposures,
        "syndromes": engine_syndromes,
        "level3": interpret(symptoms, exposures),
        "backend": backend,
        "valid_json": bool(valid_json),
        "fallback_used": bool(fallback),
        "model_engine_consistent": consistent,
        "disclaimer": DISCLAIMER,
    }

    violations = guardrail_violations(
        {"syndromes": engine_syndromes}
    )

    if isinstance(raw_text, str) and raw_text:
        violations = list(
            dict.fromkeys(
                violations + guardrail_violations(raw_text)
            )
        )

    result["guardrail_violations"] = violations

    return result


class RuleBackend:
    """Deterministic extraction backend; no language model is loaded."""

    name = "rule"

    def extract(self, text: str) -> Dict[str, Any]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Clinical input must be a non-empty string.")

        extracted = rule_extractor.extract(text)

        return finalize(
            extracted.get("symptoms", []),
            extracted.get("exposures", []),
            backend=self.name,
            valid_json=True,
            fallback=False,
        )


def _strip_code_fences(raw: str) -> str:
    """Remove optional Markdown code fences around JSON."""
    if not isinstance(raw, str):
        return ""

    cleaned = raw.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]

        cleaned = "\n".join(lines).strip()

    return cleaned


def _decode_first_json(raw: str):
    """Find the first usable JSON object in generated text."""
    if not isinstance(raw, str):
        return None

    cleaned = _strip_code_fences(raw)
    decoder = json.JSONDecoder()

    try:
        obj = json.loads(cleaned)

        if isinstance(obj, dict) and any(
            key in obj
            for key in ("symptoms", "exposures", "syndromes")
        ):
            return obj

    except (ValueError, TypeError):
        pass

    for match in re.finditer(r"\{", cleaned):
        try:
            obj, _ = decoder.raw_decode(cleaned[match.start():])
        except (ValueError, TypeError):
            continue

        if isinstance(obj, dict) and any(
            key in obj
            for key in ("symptoms", "exposures", "syndromes")
        ):
            return obj

    return None


def _repair_partial_output(raw: str, text: str):
    """
    Repair missing top-level lists and missing core fields when
    matching rule-extractor evidence is available.

    This function does not silently add rule-extracted symptoms
    that the model omitted.
    """
    obj = _decode_first_json(raw)

    if not isinstance(obj, dict):
        return raw, False

    if not isinstance(obj.get("symptoms"), list):
        return raw, False

    changed = False

    for key in ("exposures", "syndromes"):
        if key not in obj:
            obj[key] = []
            changed = True
        elif not isinstance(obj[key], list):
            return raw, False

    rule_result = rule_extractor.extract(text)

    rule_by_name = {
        symptom.get("name"): symptom
        for symptom in rule_result.get("symptoms", [])
        if isinstance(symptom, dict)
        and isinstance(symptom.get("name"), str)
    }

    aliases = {
        "shortness_of_breath": "dyspnea",
        "runny_nose": "rhinorrhea",
        "confusion": "altered_mental_status",
        "hemorrhage": "bleeding",
        "yellow_eye": "jaundice",
    }

    cleaned = []

    for original in obj["symptoms"]:
        if not isinstance(original, dict):
            cleaned.append(original)
            continue

        item = dict(original)
        name = item.get("name")

        if isinstance(name, str) and name in aliases:
            alias = aliases[name]

            if alias in SYMPTOMS:
                item["name"] = alias
                name = alias
                changed = True

        rule_symptom = rule_by_name.get(name)

        missing_core = [
            key
            for key in ("assertion", "time", "who")
            if key not in item or item[key] is None
        ]

        if missing_core and rule_symptom:
            for key in missing_core:
                if key in rule_symptom:
                    item[key] = rule_symptom[key]
                    changed = True

        if item.get("who") not in WHO and rule_symptom:
            rule_who = rule_symptom.get("who")

            if rule_who in WHO:
                item["who"] = rule_who
                changed = True

        for key in ("severity", "trend", "duration"):
            if key not in item and rule_symptom and key in rule_symptom:
                item[key] = rule_symptom[key]
                changed = True

        cleaned.append(item)

    obj["symptoms"] = cleaned

    return json.dumps(obj, ensure_ascii=False), changed


class SLMBackend:
    """Language-model extraction backend with guarded rule fallback."""

    name = "slm"

    # Refuse salvage when more than half of the clinical items are dropped.
    MAX_DROP_FRACTION = 0.5

    def __init__(
        self,
        base_model: str,
        adapter_dir: str,
        max_new_tokens: int = 448,
        device: Optional[str] = None,
        cpu_threads: int = 4,
    ):
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer

        if not isinstance(max_new_tokens, int) or max_new_tokens < 1:
            raise ValueError("max_new_tokens must be a positive integer.")

        if not isinstance(cpu_threads, int) or cpu_threads < 1:
            raise ValueError("cpu_threads must be a positive integer.")

        self.max_new_tokens = max_new_tokens
        self.torch = torch

        self.device = device or (
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        if self.device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA was requested, but CUDA is unavailable."
            )

        if self.device == "cpu":
            torch.set_num_threads(
                min(os.cpu_count() or cpu_threads, cpu_threads)
            )

        # Resolve the adapter path from the project root.
        resolved_adapter = _resolve_project_path(adapter_dir)

        if not os.path.isdir(resolved_adapter):
            raise FileNotFoundError(
                f"LoRA adapter directory does not exist: "
                f"{resolved_adapter}\n"
                "Check model.adapter_dir in config.yaml."
            )

        adapter_config = os.path.join(
            resolved_adapter, "adapter_config.json"
        )

        if not os.path.isfile(adapter_config):
            raise FileNotFoundError(
                f"Missing adapter_config.json in: {resolved_adapter}\n"
                "This directory does not appear to contain a saved "
                "PEFT adapter."
            )

        # Use the adapter tokenizer when saved; otherwise use base tokenizer.
        tokenizer_source = (
            resolved_adapter
            if os.path.isfile(
                os.path.join(resolved_adapter, "tokenizer_config.json")
            )
            else base_model
        )

        logger.info("Loading base model: %s", base_model)
        logger.info("Loading LoRA adapter: %s", resolved_adapter)
        logger.info("Inference device: %s", self.device)

        self.tok = AutoTokenizer.from_pretrained(tokenizer_source)

        if self.tok.pad_token_id is None:
            if self.tok.eos_token is not None:
                self.tok.pad_token = self.tok.eos_token
            else:
                raise RuntimeError(
                    "Tokenizer has neither a pad token nor an EOS token."
                )

        dtype = (
            torch.float16
            if self.device.startswith("cuda")
            else torch.float32
        )

        base = AutoModelForCausalLM.from_pretrained(
            base_model,
            torch_dtype=dtype,
        )

        model = PeftModel.from_pretrained(
            base, resolved_adapter
        ).merge_and_unload()

        self.model = model.to(self.device).eval()
        self.adapter_dir = resolved_adapter

        eos_ids = [
            self.tok.eos_token_id,
            self.tok.convert_tokens_to_ids("<|im_end|>"),
        ]

        self.eos_ids = sorted(
            {
                token_id
                for token_id in eos_ids
                if isinstance(token_id, int) and token_id >= 0
            }
        )

    def raw_generate(self, text: str) -> str:
        """Generate raw model text without trusting it as structured data."""
        messages = [
            {"role": "system", "content": TASK_INSTRUCTION},
            {
                "role": "user",
                "content": (
                    "Clinical text (extract only supported facts):\n"
                    f"{text}\n"
                    "Return exactly one complete JSON object. "
                    "Do not omit required fields."
                ),
            },
        ]

        encoded = self.tok.apply_chat_template(
            messages,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,
        ).to(self.device)

        pad_token_id = self.tok.pad_token_id
        if pad_token_id is None:
            pad_token_id = self.tok.eos_token_id

        with self.torch.no_grad():
            generated = self.model.generate(
                **encoded,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                pad_token_id=pad_token_id,
                eos_token_id=self.eos_ids or self.tok.eos_token_id,
            )

        prompt_length = encoded["input_ids"].shape[1]
        new_tokens = generated[0][prompt_length:]

        return self.tok.decode(
            new_tokens,
            skip_special_tokens=True,
        )

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Generate once, then strict parse -> repair -> guarded salvage
        -> rule fallback.
        """
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Clinical input must be a non-empty string.")

        last_error = None
        raw = ""

        try:
            raw = self.raw_generate(text)

            obj, valid, _ = parse_model_output_ex(
                raw, salvage=False
            )

            raw_valid = valid
            repaired = False
            dropped = []
            clinical_drops = []
            candidate = raw

            if not valid:
                candidate, repaired = _repair_partial_output(
                    raw, text
                )

                obj, valid, _ = parse_model_output_ex(
                    candidate, salvage=False
                )

            if not valid:
                obj, valid, dropped = parse_model_output_ex(
                    candidate, salvage=True
                )

                if valid:
                    clinical_drops = [
                        item
                        for item in dropped
                        if not str(item).startswith("syndrome")
                    ]

                    raw_obj = _decode_first_json(candidate) or {}

                    n_items = (
                        len(raw_obj.get("symptoms", []))
                        + len(raw_obj.get("exposures", []))
                    )

                    if (
                        clinical_drops
                        and n_items
                        and len(clinical_drops) / n_items
                        > self.MAX_DROP_FRACTION
                    ):
                        last_error = (
                            "salvage refused: dropped "
                            f"{len(clinical_drops)} of {n_items} items "
                            f"{clinical_drops}"
                        )
                        valid = False

            if valid and isinstance(obj, dict):
                result = finalize(
                    obj["symptoms"],
                    obj["exposures"],
                    obj.get("syndromes"),
                    backend=self.name,
                    valid_json=True,
                    fallback=False,
                    raw_text=raw,
                )

                result["model_output_repaired"] = bool(
                    repaired and not raw_valid
                )
                result["raw_model_output_valid"] = bool(raw_valid)
                result["items_dropped"] = dropped
                result["partial_output"] = bool(clinical_drops)

                return result

            last_error = (
                last_error
                or "model output failed validation and could not be salvaged"
            )

            logger.warning(
                "SLM validation failed. repaired=%s. Raw output: %r",
                repaired,
                raw[:600],
            )

        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            logger.warning("SLM generation failed: %s", last_error)

        logger.error("SyndraLens using rule fallback: %s", last_error)

        extracted = rule_extractor.extract(text)

        result = finalize(
            extracted.get("symptoms", []),
            extracted.get("exposures", []),
            backend=self.name,
            valid_json=False,
            fallback=True,
            raw_text=raw,
        )

        result["inference_error"] = last_error or "unknown inference failure"
        result["model_output_repaired"] = False
        result["raw_model_output_valid"] = False
        result["items_dropped"] = []
        result["partial_output"] = False

        return result


def load_backend(kind: Optional[str] = None, cfg: Optional[dict] = None):
    """Load the explicitly configured extraction backend."""

    kind = kind or os.environ.get("SYNDRALENS_BACKEND", "rule")
    kind = kind.strip().lower()

    if kind == "rule":
        return RuleBackend()

    if kind != "slm":
        raise ValueError(
            f"Unsupported backend {kind!r}. Choose 'rule' or 'slm'."
        )

    if not isinstance(cfg, dict):
        raise ValueError(
            "SLM backend requires a config dictionary containing 'model'."
        )

    model_cfg = cfg.get("model")

    if not isinstance(model_cfg, dict):
        raise ValueError("Configuration is missing the 'model' section.")

    base_model = model_cfg.get("base_model")
    adapter_dir = model_cfg.get("adapter_dir")
    max_new_tokens = model_cfg.get("max_new_tokens", 448)

    if not isinstance(base_model, str) or not base_model.strip():
        raise ValueError(
            "model.base_model must be a non-empty string."
        )

    if not isinstance(adapter_dir, str) or not adapter_dir.strip():
        raise ValueError(
            "model.adapter_dir must be a non-empty string."
        )

    return SLMBackend(
        base_model=base_model,
        adapter_dir=adapter_dir,
        max_new_tokens=max_new_tokens,
    )