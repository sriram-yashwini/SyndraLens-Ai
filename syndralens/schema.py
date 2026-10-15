
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from .ontology import (
    ASSERTIONS,
    EXPOSURE_ASSERTIONS,
    EXPOSURES,
    FORBIDDEN_TERMS,
    SEVERITIES,
    SIGNAL_LEVELS,
    SYMPTOMS,
    SYNDROMES,
    TIMES,
    TRENDS,
    WHO,
)

log = logging.getLogger("syndralens.schema")


def _labels(values) -> str:
    """Comma-separated label list; keeps list order, sorts sets/dicts."""
    items = list(values) if isinstance(values, (list, tuple)) else sorted(values)
    return ", ".join(str(v) for v in items)


_FORMAT_EXAMPLE = json.dumps(
    {
        "symptoms": [
            {
                "name": "fever",
                "assertion": "present",
                "time": "current",
                "who": "patient",
                "severity": "unspecified",
                "trend": "unknown",
                "duration": None,
            }
        ],
        "exposures": [],
        "syndromes": [],
    },
    separators=(",", ":"),
)

TASK_INSTRUCTION = (
    "Extract symptoms, exposures and syndromes from clinical text. "
    "Return ONE JSON object only, with no other text. "
    "It has three arrays. Each symptom has name, assertion, time, who, severity, "
    "trend, duration. Each exposure has type, assertion. "
    "Each syndrome has syndrome, signal. "
    "Allowed labels only. "
    f"name: {_labels(SYMPTOMS)}. "
    f"assertion: {_labels(ASSERTIONS)}. "
    f"time: {_labels(TIMES)}. "
    f"who: {_labels(WHO)}. "
    f"severity: {_labels(SEVERITIES)}. "
    f"trend: {_labels(TRENDS)}. "
    f"exposure type: {_labels(EXPOSURES)}. "
    f"exposure assertion: {_labels(EXPOSURE_ASSERTIONS)}. "
    f"syndrome: {_labels(SYNDROMES)}. "
    f"signal: {_labels(SIGNAL_LEVELS)}. "
    "Syndrome names are never symptom names. Negated symptom = absent. "
    "Relative or other person = who family/other. Earlier episode = past. "
    "duration is null if not stated. Do not guess or name diseases. "
    f"Format example (not an answer): {_FORMAT_EXAMPLE}"
)


def new_symptom(
    name: str,
    assertion: str = "present",
    time: str = "current",
    who: str = "patient",
    severity: str = "unspecified",
    trend: str = "unknown",
    duration: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a symptom object using the project's established schema."""
    return {
        "name": name,
        "assertion": assertion,
        "time": time,
        "who": who,
        "severity": severity,
        "trend": trend,
        "duration": clean_duration(duration) if duration else None,
    }


def _pick(value: Any, allowed, default: Any) -> Any:
    """Return value only when it belongs to the allowed ontology."""
    try:
        return value if value in allowed else default
    except (TypeError, ValueError):
        return default


def _as_list(value: Any) -> List[Any]:
    """Accept lists only; reject malformed annotation containers."""
    if not isinstance(value, list):
        raise ValueError(f"Expected a list in annotation data, got {type(value).__name__}")
    return value


SYMPTOM_ALIASES = {
    "shortness_of_breath": "dyspnea",
    "runny_nose": "rhinorrhea",
    "confusion": "altered_mental_status",
    "hemorrhage": "bleeding",
    "yellow_eye": "jaundice",
}


def normalize_symptom(s: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate and normalize one model-produced symptom object."""
    if not isinstance(s, dict):
        return None

    name = s.get("name")
    if isinstance(name, str):
        name = name.strip().lower()
        name = SYMPTOM_ALIASES.get(name, name)
    if not isinstance(name, str) or name not in SYMPTOMS:
        return None

    assertion = s.get("assertion")
    time_val = s.get("time")
    who_val = s.get("who")

    if isinstance(assertion, str):
        assertion = assertion.strip().lower()
    if isinstance(time_val, str):
        time_val = time_val.strip().lower()
    if isinstance(who_val, str):
        who_val = who_val.strip().lower()

    if assertion not in ASSERTIONS:
        return None
    if time_val not in TIMES:
        return None
    if who_val not in WHO:
        return None

    duration = s.get("duration")
    if isinstance(duration, (int, float)) and not isinstance(duration, bool):
        duration = f"{duration} days"
    duration = clean_duration(str(duration)) if duration else None

    return {
        "name": name,
        "assertion": assertion,
        "time": time_val,
        "who": who_val,
        "severity": _pick(s.get("severity"), SEVERITIES, "unspecified"),
        "trend": _pick(s.get("trend"), TRENDS, "unknown"),
        "duration": duration,
    }


def normalize_exposure(e: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Validate and normalize one exposure object."""
    if not isinstance(e, dict):
        return None

    exposure_type = e.get("type")
    assertion = e.get("assertion")

    if isinstance(exposure_type, str):
        exposure_type = exposure_type.strip().lower()
    if isinstance(assertion, str):
        assertion = assertion.strip().lower()

    if not isinstance(exposure_type, str) or exposure_type not in EXPOSURES:
        return None
    if assertion not in EXPOSURE_ASSERTIONS:
        return None

    return {"type": exposure_type, "assertion": assertion}


def infer_exposures(symptoms: Any, exposures: Any) -> List[Dict[str, str]]:
    """Normalize explicitly reported exposures; never infer contact from symptoms alone."""
    if not isinstance(exposures, list):
        raise ValueError("exposures must be a list")
    normalized_exposures = []
    for item in exposures:
        normalized = normalize_exposure(item)
        if normalized is not None:
            normalized_exposures.append(normalized)
    return normalized_exposures


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        candidate = json.loads(cleaned)
        if isinstance(candidate, dict):
            return candidate
    except (json.JSONDecodeError, ValueError):
        pass

    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", cleaned):
        try:
            candidate, _ = decoder.raw_decode(cleaned[match.start():])
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(candidate, dict):
            return candidate
    return None


def parse_model_output_ex(
    text: str,
    salvage: bool = False,
) -> Tuple[Optional[Dict[str, Any]], bool, List[str]]:
    """Parse and validate model output.

    strict (salvage=False): any invalid item rejects the whole output.
    salvage=True: invalid individual items are DROPPED (never guessed or
    replaced). If symptoms existed but every one was dropped, the output is
    rejected so the caller can fall back to the rule extractor.

    Returns (object_or_None, is_valid, list_of_dropped_item_descriptions).
    """
    if not isinstance(text, str) or not text.strip():
        return None, False, []

    obj = _extract_json_object(text)
    if obj is None:
        return None, False, []

    for key in ("symptoms", "exposures", "syndromes"):
        if key not in obj:
            log.debug("rejected: missing top-level field %r", key)
            return None, False, []
        if not isinstance(obj[key], list):
            log.debug("rejected: %r must be a list", key)
            return None, False, []

    dropped: List[str] = []

    symptoms = []
    for index, item in enumerate(obj["symptoms"]):
        normalized = normalize_symptom(item)
        if normalized is None:
            desc = f"symptom[{index}]={item.get('name') if isinstance(item, dict) else item!r}"
            if not salvage:
                log.debug("rejected: invalid %s", desc)
                return None, False, []
            dropped.append(desc)
            continue
        symptoms.append(normalized)

    if salvage and obj["symptoms"] and not symptoms:
        return None, False, dropped

    exposures = []
    for index, item in enumerate(obj["exposures"]):
        normalized = normalize_exposure(item)
        if normalized is None:
            desc = f"exposure[{index}]={item.get('type') if isinstance(item, dict) else item!r}"
            if not salvage:
                log.debug("rejected: invalid %s", desc)
                return None, False, []
            dropped.append(desc)
            continue
        exposures.append(normalized)

    syndromes = []
    for index, item in enumerate(obj["syndromes"]):
        ok = isinstance(item, dict)
        syndrome = signal = None
        if ok:
            syndrome = item.get("syndrome")
            signal = item.get("signal")
            if isinstance(syndrome, str):
                syndrome = syndrome.strip().lower()
            if isinstance(signal, str):
                signal = signal.strip().lower()
            ok = (
                isinstance(syndrome, str)
                and syndrome in SYNDROMES
                and signal in SIGNAL_LEVELS
            )
        if not ok:
            desc = f"syndrome[{index}]"
            if not salvage:
                log.debug("rejected: invalid %s", desc)
                return None, False, []
            dropped.append(desc)
            continue
        syndromes.append({"syndrome": syndrome, "signal": signal})

    return (
        {"symptoms": symptoms, "exposures": exposures, "syndromes": syndromes},
        True,
        dropped,
    )


def parse_model_output(text: str) -> Tuple[Optional[Dict[str, Any]], bool]:
    """Strict parse (kept for backwards compatibility)."""
    obj, valid, _ = parse_model_output_ex(text, salvage=False)
    return obj, valid


def serialize_target(symptoms: Any, exposures: Any, syndromes: Any) -> str:
    """Serialize normalized annotations into compact JSON for SLM training."""
    raw_symptoms = _as_list(symptoms)
    raw_exposures = _as_list(exposures)
    normalized_symptoms = [normalize_symptom(raw) for raw in raw_symptoms]
    normalized_exposures = [normalize_exposure(raw) for raw in raw_exposures]
    if any(item is None for item in normalized_symptoms):
        raise ValueError("Invalid symptom annotation; refusing to silently drop a training label.")
    if any(item is None for item in normalized_exposures):
        raise ValueError("Invalid exposure annotation; refusing to silently drop a training label.")

    normalized_syndromes = []
    for item in _as_list(syndromes):
        if not isinstance(item, dict):
            raise ValueError("Invalid syndrome annotation; refusing to silently drop a training label.")
        syndrome = item.get("syndrome")
        signal = item.get("signal")
        if isinstance(syndrome, str):
            syndrome = syndrome.strip().lower()
        if isinstance(signal, str):
            signal = signal.strip().lower()

        if not isinstance(syndrome, str) or syndrome not in SYNDROMES:
            raise ValueError(f"Unknown syndrome annotation: {syndrome!r}")
        if signal not in SIGNAL_LEVELS:
            raise ValueError(f"Invalid syndrome signal: {signal!r}")
        normalized_syndromes.append({"syndrome": syndrome, "signal": signal})

    obj = {
        "symptoms": normalized_symptoms,
        "exposures": normalized_exposures,
        "syndromes": normalized_syndromes,
    }

    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def _forbidden_term_matches(text: str) -> List[str]:
    """Find forbidden terms using case-insensitive word boundaries."""
    hits = []
    for term in FORBIDDEN_TERMS:
        if not isinstance(term, str) or not term.strip():
            continue
        pattern = r"(?<!\w)" + re.escape(term.strip()) + r"(?!\w)"
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(term)
    return hits


def guardrail_violations(obj_or_text: Any) -> List[str]:
    """Report forbidden terms and unknown syndromes in model output."""
    hits: List[str] = []

    if isinstance(obj_or_text, str):
        hits.extend(_forbidden_term_matches(obj_or_text))
        return list(dict.fromkeys(hits))

    if not isinstance(obj_or_text, dict):
        return ["invalid_output_type"]

    try:
        text = json.dumps(obj_or_text, ensure_ascii=False)
    except (TypeError, ValueError):
        return ["unserializable_output"]

    hits.extend(_forbidden_term_matches(text))

    for item in _as_list(obj_or_text.get("syndromes", [])):
        if not isinstance(item, dict):
            continue
        syndrome = item.get("syndrome")
        if not isinstance(syndrome, str) or syndrome not in SYNDROMES:
            hits.append(f"unknown_syndrome:{syndrome}")

    return list(dict.fromkeys(hits))


def clean_duration(text: Optional[str]) -> Optional[str]:
    """Normalize common duration expressions."""
    if not isinstance(text, str):
        return None

    text = re.sub(r"\s+", " ", text.lower()).strip()
    if not text or text == "null":
        return None

    text = re.sub(r"^(?:for\s+)+", "", text)
    text = re.sub(r"^x\s+", "", text)

    number_words = {
        "a": "1", "an": "1", "one": "1", "two": "2", "three": "3",
        "four": "4", "five": "5", "six": "6", "seven": "7",
        "eight": "8", "nine": "9", "ten": "10",
    }

    parts = text.split()
    if parts:
        parts[0] = number_words.get(parts[0], parts[0])
    text = " ".join(parts)

    unit_patterns = {
        r"\b(?:hr|hrs|hour|hours)\b": "hours",
        r"\b(?:min|mins|minute|minutes)\b": "minutes",
        r"\b(?:day|days)\b": "days",
        r"\b(?:wk|wks|week|weeks)\b": "weeks",
        r"\b(?:mo|mos|month|months)\b": "months",
        r"\b(?:yr|yrs|year|years)\b": "years",
    }

    for pattern, replacement in unit_patterns.items():
        text = re.sub(pattern, replacement, text)

    if re.match(r"^1\s+", text):
        text = re.sub(
            r"\b(hours|minutes|days|weeks|months|years)\b",
            lambda match: match.group(1)[:-1],
            text,
        )

    return text or None
