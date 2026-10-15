
import math
from typing import Any, Dict, List, Mapping, Optional, Set

from .ontology import (
    ASSERTION_WEIGHT,
    DISCLAIMER,
    SEVERITY_WEIGHT,
    SIGNAL_THRESHOLDS,
    SYNDROMES,
    TIME_WEIGHT,
    TREND_WEIGHT,
)


# ---------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------

def _normalise_name(value: Any) -> Optional[str]:
    """Normalize symptom names without changing their meaning."""
    if not isinstance(value, str):
        return None

    name = value.strip().lower()

    if not name:
        return None

    return name


def _finite_number(value: Any) -> Optional[float]:
    """Convert a value to a finite float, or return None."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None

    if not math.isfinite(number):
        return None

    return number


def _valid_weight(value: Any) -> Optional[float]:
    """Accept only finite, non-negative numeric weights."""
    number = _finite_number(value)

    if number is None or number < 0:
        return None

    return number


# ---------------------------------------------------------------------
# Symptom evidence scoring
# ---------------------------------------------------------------------

def _symptom_strength(s: Dict[str, Any]) -> float:
    """
    Calculate the evidence strength of one patient symptom.

    Family/contact symptoms, absent symptoms, hypothetical symptoms,
    past symptoms, and invalid ontology attributes contribute zero.
    """
    if not isinstance(s, dict):
        return 0.0

    if s.get("who") != "patient":
        return 0.0

    assertion = s.get("assertion")
    time = s.get("time")
    severity = s.get("severity")
    trend = s.get("trend")

    if assertion not in {"present", "possible"}:
        return 0.0

    if time not in {"current", "chronic"}:
        return 0.0

    if assertion not in ASSERTION_WEIGHT:
        return 0.0

    if time not in TIME_WEIGHT:
        return 0.0

    if severity not in SEVERITY_WEIGHT:
        return 0.0

    if trend not in TREND_WEIGHT:
        return 0.0

    assertion_weight = _finite_number(
        ASSERTION_WEIGHT[assertion]
    )
    time_weight = _finite_number(TIME_WEIGHT[time])
    severity_weight = _finite_number(SEVERITY_WEIGHT[severity])
    trend_weight = _finite_number(TREND_WEIGHT[trend])

    factors = (
        assertion_weight,
        time_weight,
        severity_weight,
        trend_weight,
    )

    if any(value is None or value < 0 for value in factors):
        return 0.0

    strength = (
        assertion_weight
        * time_weight
        * severity_weight
        * trend_weight
    )

    if not math.isfinite(strength):
        return 0.0

    return max(0.0, strength)


# ---------------------------------------------------------------------
# Signal levels
# ---------------------------------------------------------------------

def _level(score: float) -> str:
    """Convert a finite numeric score to a signal level."""
    numeric_score = _finite_number(score)

    if numeric_score is None or numeric_score < 0:
        return "none"

    thresholds = {}

    for level_name in ("weak", "moderate", "strong"):
        value = _finite_number(
            SIGNAL_THRESHOLDS.get(level_name)
        )

        if value is None or value < 0:
            return "none"

        thresholds[level_name] = value

    if not (
        thresholds["weak"]
        <= thresholds["moderate"]
        <= thresholds["strong"]
    ):
        return "none"

    if numeric_score >= thresholds["strong"]:
        return "strong"

    if numeric_score >= thresholds["moderate"]:
        return "moderate"

    if numeric_score >= thresholds["weak"]:
        return "weak"

    return "none"


# ---------------------------------------------------------------------
# Syndrome configuration
# ---------------------------------------------------------------------

def _syndrome_weights(
    spec: Mapping[str, Any],
) -> Dict[str, float]:
    """
    Return valid weights for one syndrome.

    Explicit weights take priority. If no usable explicit weights
    exist, required symptom names receive equal weight.
    """
    configured = spec.get("weights", {})

    if isinstance(configured, dict) and configured:
        result: Dict[str, float] = {}

        for symptom_name, raw_weight in configured.items():
            name = _normalise_name(symptom_name)
            weight = _valid_weight(raw_weight)

            if name is None or weight is None or weight <= 0:
                continue

            result[name] = weight

        if result:
            return result

    required = spec.get("require", [])
    names: Set[str] = set()

    if isinstance(required, (list, tuple)):
        for group in required:
            if isinstance(group, str):
                name = _normalise_name(group)

                if name is not None:
                    names.add(name)

            elif isinstance(group, (list, tuple, set)):
                for item in group:
                    name = _normalise_name(item)

                    if name is not None:
                        names.add(name)

    return {name: 1.0 for name in sorted(names)}


def _requirements_met(
    required_groups: Any,
    eligible_symptoms: Set[str],
) -> bool:
    """
    Check syndrome requirements.

    Semantics:
      - Each group requires at least one matching symptom (OR).
      - All groups must be satisfied (AND).
      - An empty requirements list imposes no requirement.
    """
    if not isinstance(required_groups, (list, tuple)):
        return False

    for group in required_groups:
        if isinstance(group, str):
            group_names = [_normalise_name(group)]

        elif isinstance(group, (list, tuple, set)):
            group_names = [
                _normalise_name(item)
                for item in group
            ]

        else:
            return False

        valid_names = {
            name for name in group_names if name is not None
        }

        # Empty groups cannot be satisfied.
        if not valid_names:
            return False

        if not valid_names.intersection(eligible_symptoms):
            return False

    return True


# ---------------------------------------------------------------------
# Main syndrome engine
# ---------------------------------------------------------------------

def compute_syndromes(
    symptoms: List[Dict[str, Any]],
    detailed: bool = False,
) -> List[Dict[str, Any]]:
    """
    Return active syndromes, strongest first.

    Only eligible patient symptoms contribute to scores.
    Each canonical symptom name contributes at most once.

    detailed=True adds score, assertion-based confidence,
    uncertainty, and evidence names.

    Confidence is a rule-derived indicator, not calibrated
    clinical probability.
    """
    if not isinstance(symptoms, list):
        symptoms = []

    # Keep the strongest eligible mention of each normalized name.
    strength: Dict[str, float] = {}
    assertion_confidence: Dict[str, float] = {}

    for symptom in symptoms:
        if not isinstance(symptom, dict):
            continue

        name = _normalise_name(symptom.get("name"))

        if name is None:
            continue

        value = _symptom_strength(symptom)

        if value <= 0:
            continue

        previous = strength.get(name, 0.0)

        if value > previous:
            strength[name] = value

            assertion = symptom.get("assertion")
            confidence_value = _finite_number(
                ASSERTION_WEIGHT.get(assertion)
            )

            assertion_confidence[name] = (
                max(0.0, min(1.0, confidence_value))
                if confidence_value is not None
                else 0.0
            )

    eligible_symptoms = set(strength.keys())
    results: List[Dict[str, Any]] = []

    for syndrome_name, spec in SYNDROMES.items():
        if not isinstance(syndrome_name, str):
            continue

        if not isinstance(spec, dict):
            continue

        required_groups = spec.get("require", [])

        if not _requirements_met(
            required_groups,
            eligible_symptoms,
        ):
            continue

        weights = _syndrome_weights(spec)

        used = {
            name: weight
            for name, weight in weights.items()
            if strength.get(name, 0.0) > 0
        }

        if not used:
            continue

        score = sum(
            weight * strength[name]
            for name, weight in used.items()
        )

        # Protect against invalid configuration or arithmetic overflow.
        if not math.isfinite(score) or score < 0:
            continue

        signal = _level(score)

        if signal == "none":
            continue

        item = {
            "syndrome": syndrome_name,
            "signal": signal,
        }

        if detailed:
            confidence_values = [
                assertion_confidence[name]
                for name in used
            ]

            confidence = (
                sum(confidence_values) / len(confidence_values)
                if confidence_values
                else 0.0
            )

            confidence = max(0.0, min(1.0, confidence))

            item.update({
                "score": round(score, 2),
                "confidence": round(confidence, 2),
                "uncertainty": round(1.0 - confidence, 2),
                "evidence": sorted(used.keys()),
            })

        results.append(item)

    # Suppress nonspecific fever output when a more specific
    # syndrome signal is active.
    if any(
        result["syndrome"] != "febrile_nonspecific"
        for result in results
    ):
        results = [
            result
            for result in results
            if result["syndrome"] != "febrile_nonspecific"
        ]

    signal_order = {
        "strong": 3,
        "moderate": 2,
        "weak": 1,
    }

    results.sort(
        key=lambda result: (
            -signal_order.get(result["signal"], 0),
            result["syndrome"],
        )
    )

    return results


# ---------------------------------------------------------------------
# API/dashboard interpretation
# ---------------------------------------------------------------------

def interpret(
    symptoms: List[Dict[str, Any]],
    exposures=None,
) -> Dict[str, Any]:
    """
    Build the Level-3 record for API and dashboard consumers.

    The context field reports symptom mentions and exposure types;
    it does not claim to count unique people or confirmed cases.
    """
    symptoms = symptoms if isinstance(symptoms, list) else []
    exposures = exposures if isinstance(exposures, list) else []

    non_patient_mentions = sum(
        1
        for symptom in symptoms
        if isinstance(symptom, dict)
        and symptom.get("who") in {"family", "other"}
        and symptom.get("assertion") == "present"
    )

    exposure_types = {
        exposure.get("type")
        for exposure in exposures
        if isinstance(exposure, dict)
        and exposure.get("assertion") == "present"
        and isinstance(exposure.get("type"), str)
        and exposure.get("type").strip()
    }

    return {
        "syndromes": compute_syndromes(
            symptoms,
            detailed=True,
        ),
        "context": {
            # Retain the original key for compatibility with
            # existing dashboard/API consumers.
            "household_or_contact_cases": non_patient_mentions,
            "non_patient_symptom_mentions": non_patient_mentions,
            "exposures_present": sorted(exposure_types),
        },
        "interpretation": DISCLAIMER,
    }
