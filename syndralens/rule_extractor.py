
import re
from typing import Any, Dict, List, Optional

from .ontology import IMPLIED_NEGATION, MULTI_ABBR, SYMPTOMS
from .schema import clean_duration, infer_exposures, new_symptom

# --------------------------------------------------------------------------- lexicon regexes
def _alt(words):
    return "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))

_FORMAL_RX = []
_COLLOQUIAL_RX = []

for _name, _spec in SYMPTOMS.items():
    if _spec.get("formal"):
        _FORMAL_RX.append((
            _name,
            re.compile(
                r"(?<![\w])(?:" + _alt(_spec["formal"]) + r")(?![\w])",
                re.I,
            ),
        ))

    if _spec.get("colloquial"):
        _COLLOQUIAL_RX.append((
            _name,
            re.compile(
                r"(?<![\w])(?:" + _alt(_spec["colloquial"]) + r")(?![\w])",
                re.I,
            ),
        ))

_ABBR = {a: n for n, spec in SYMPTOMS.items() for a in spec["abbr"]}
_ABBR_RX = re.compile(r"(?<![\w/])(" + _alt(list(_ABBR)) + r")(?![\w/])")
_MULTI_RX = re.compile(r"(?<![\w/])(" + _alt(list(MULTI_ABBR)) + r")(?![\w/])")
_IMPLIED_RX = re.compile(r"(?<![\w])(" + _alt(list(IMPLIED_NEGATION)) + r")(?![\w])", re.I)

# --------------------------------------------------------------------------- trigger regexes
_REL_FAMILY = (r"(?:wife|husband|spouse|mother|father|mom|dad|son|daughter|brother|sister|sibling|"
               r"grandmother|grandfather|grandson|granddaughter|family members?|household members?)")
_REL_OTHER = r"(?:roommate|co-?workers?|colleague|neighbou?r|classmate|friend)"
_AGE = r"(?:\d+[- ](?:year|yr|month)s?[- ]old\s+)?"
_POSS = r"(?:(?:his|her|their|my|our|the patient'?s|patient'?s|a|an|the)\s+)?"
_VERB = (r"(?:(?:also|now|recently|just|both|all)\s+)*"
         r"(?:has|had|have|having|developed|developing|is having|was having|complains? of|complained of|"
         r"complaining of|is complaining of|presented with|with|suffers? from|got|caught|"
         r"(?:is|are|was|were)\s+(?:also\s+)?(?:sick with|ill with|suffering from|complaining of|having)|"
         r"(?:is|are|was|were)\s+(?:also\s+)?(?=\w+ing\b))")

_TRIGGERS = [
    ("unc", re.compile(r"(?:\b(?:cannot rule out|can't rule out|unable to rule out|not ruled out|cannot exclude|"
                       r"maybe|possible|possibly|probable|probably|suspected|suspect|suspicious for|concern for|"
                       r"concerning for|concerned about|r/o|rule out|rule-out|to rule out|likely|questionable|"
                       r"may have|might have|could be|could have|suggestive of|query)\b|\?)", re.I)),
    ("neg", re.compile(r"\b(?:no evidence of|no history of|no signs? of|no longer|negative for|neg for|free of|"
                       r"absence of|denies|denied|denying|without|never|absent|not|no)\b", re.I)),
    ("hyp", re.compile(r"\b(?:returns?(?: to (?:the )?[\w ]{1,25}?)? if|come back if|call (?:us |the clinic |your doctor )?if|"
                       r"if (?:you |he |she |they |the patient )?(?:develops?|have|has|get|gets|experiences?|"
                       r"notices?|worsens?|starts?)|should (?:you |he |she |they |the patient )?"
                       r"(?:develop|have|experience|notice)|monitor for|watch for|look out for|risk of|"
                       r"in case of|return precautions for|return for)\b", re.I)),
    ("fam", re.compile(r"\b" + _POSS + _AGE + r"(?:" + _REL_FAMILY + r")\s+" + _VERB + r"\b", re.I)),
    ("oth", re.compile(r"\b" + _POSS + r"(?:" + _REL_OTHER + r")\s+" + _VERB + r"\b", re.I)),
    ("famhist", re.compile(r"\b(?:family history of|fhx of|fh of)\b", re.I)),
    ("self", re.compile(r"\b(?:patient|pt|he|she|i|me|myself)\s+(?:also\s+|now\s+)?"
                        r"(?:has|had|have|reports?|reported|complains? of|complained of|presents? with|"
                        r"presented with|developed|notes?|c/o|is having|was having|experiences?)\b", re.I)),
    ("past", re.compile(r"\b(?:history of(?! present)|hx of|h/o|previous(?:ly)?|prior|used to have|"
                        r"in the past|status post)\b", re.I)),
    ("chronic", re.compile(r"\b(?:chronic(?:ally)?|longstanding|long-standing|baseline|recurrent)\b", re.I)),
]

# a scope terminator stops negation/uncertainty/attribution from spreading further
_TERM = re.compile(r"\b(?:but|however|although|though|except|whereas|yet|while|which|"
                   r"reports?|complains? of|c/o|presents? with|endorses|admits|positive for)\b|"
                   r"(?<!not\s)(?<!never\s)\bhas\b|;", re.I)

_POST_NEG = re.compile(r"^\s*[:,-]?\s*(?:was |is |were |are )?(?:denied|absent|negative|not present|"
                       r"not reported|ruled out|none|neg)\b", re.I)
_POST_UNC = re.compile(r"^\s*\?")
_POST_PAST = re.compile(
    r"^[^.;]{0,40}?\b(?:resolved|has resolved|subsided|last (?:night|week|month|year)|"
    r"\d+ days? ago|\d+ weeks? ago|\d+ months? ago|\d+ years? ago|"
    r"years? ago|months? ago|weeks? ago|days? ago|in the past)\b", re.I
)
_PRE_PAST = re.compile(r"\b(?:i|he|she|they|patient|pt)\s+had\s+(?:(?:a|an|the)\s+)?$", re.I)
_POST_CHRONIC = re.compile(r"^[^.;]{0,40}?\b(?:chronic|longstanding|long-standing|since childhood|for years)\b",
                           re.I)

# --------------------------------------------------------------------------- modifiers
_SEVERE = re.compile(r"\b(?:severe|severely|intense|extreme|profuse|excruciating|worst|marked|high-grade|"
                     r"high grade|violent|heavy)\b", re.I)
_MODERATE = re.compile(r"\b(?:moderate|moderately)\b", re.I)
_MILD = re.compile(r"\b(?:mild|mildly|slight|minimal|low-grade|low grade|occasional|minor)\b", re.I)
_POST_SEV = re.compile(r"^\s*(?:is |are |was |were |has been )?(?:very |quite |fairly )?(severe|moderate|mild)\b", re.I)

_WORSEN = re.compile(r"\b(?:worsen\w*|increas\w*|progress\w*|escalat\w*|getting worse|gets worse|more frequent|"
                     r"rising|intensif\w*|aggravat\w*|spiking|getting more)\b", re.I)
_IMPROVE = re.compile(r"\b(?:improv\w*|getting better|better|resolving|decreas\w*|subsid\w*|less frequent|"
                      r"diminish\w*|settling)\b", re.I)
_STABLE = re.compile(r"\b(?:stable|unchanged|remained the same|same as before)\b", re.I)

_NUM = r"(\d+(?:\.\d+)?|a|an|one|two|three|four|five|six|seven|eight|nine|ten|few|several|couple of)"
_DUR1 = re.compile(r"\b(?:for(?: the (?:past|last))?|x|since|(?:over|in) the (?:past|last)|past|last)\s*"
                   r"(?:about |approximately |around |~)?" + _NUM + r"[\s-]*(hours?|hrs?|days?|weeks?|months?|years?)\b",
                   re.I)
_DUR2 = re.compile(r"\b" + _NUM + r"[- ](hour|day|week|month|year)s?[- ](?:history|course)\b", re.I)
_DUR3 = re.compile(r"\bsince yesterday\b", re.I)

# --------------------------------------------------------------------------- exposures
_EXPOSURE_RX = [
    ("sick_contact", re.compile(
        r"\b(?:sick contacts?|ill contacts?|sick (?:co-?workers?|classmates?|family members?|household members?|"
        r"relatives?)|exposed to (?:someone|a person|people|individuals)(?: who (?:is|was|were|are))? (?:sick|ill)|"
        r"contact with (?:a |someone |people )?(?:who (?:is |was )?)?(?:sick|ill|infected)|"
        r"(?:family members?|household members?|co-?workers?|classmates?|roommates?) (?:are |were |also )*"
        r"(?:sick|ill|unwell)|(?:wife|husband|spouse|son|daughter|brother|sister|mother|father|roommate|"
        r"neighbou?r|colleague) (?:is |was |are |were |also |has been )*(?:sick|ill|unwell))\b", re.I)),
    ("travel", re.compile(r"\b(?:recent travel|returned from|travel(?:l?ed)? (?:to|from|history)|recent trip|"
                          r"just came back from|international travel|trip abroad|travel abroad)\b", re.I)),
    ("animal_contact", re.compile(r"\b(?:poultry|chickens?|birds?|bats?|livestock|cattle|pigs?|swine|rodents?|"
                                  r"rats?|animal (?:contact|exposure|bite)|dog bite|farm animals?|camels?)\b", re.I)),
    ("healthcare_contact", re.compile(r"\b(?:nursing home|long[- ]term care|dialysis|health ?care worker|"
                                      r"recent hospitali[sz]ation|hospital visit|visited (?:a |the )?hospital)\b",
                                      re.I)),
    ("food_water", re.compile(r"\b(?:contaminated (?:food|water)|street food|undercooked|raw (?:meat|milk|seafood|eggs?)|"
                              r"unsafe water|restaurant|buffet|well water|flood ?water)\b", re.I)),
    ("vector", re.compile(r"\b(?:mosquito(?:es)?(?: bites?)?|tick bites?)\b", re.I)),
]

# --------------------------------------------------------------------------- vitals
_TEMP_RX = re.compile(r"\btemp(?:erature)?\b[^\d\n]{0,12}(\d{2,3}(?:\.\d+)?)\s*°?\s*([FfCc])?\b", re.I)
_SPO2_RX = re.compile(r"\b(?:spo2|sp02|o2\s*sat(?:uration)?s?|oxygen saturation|sats?)\b[^\d\n]{0,12}"
                      r"(\d{2,3})\s*%?", re.I)
_SENT_SPLIT = re.compile(r"(?<=[.;!?])\s+|\n+")


# =========================================================================== helpers
def _find_triggers(sent: str):
    found = []
    for kind, rx in _TRIGGERS:
        for m in rx.finditer(sent):
            found.append((m.start(), m.end(), kind))
    found.sort(key=lambda t: (-(t[1] - t[0]), t[0]))
    chosen = []
    for t in found:
        if all(t[1] <= c[0] or t[0] >= c[1] for c in chosen):
            chosen.append(t)
    chosen.sort()
    return chosen


def _nearest(trigs, kinds, pos: int, sent: str, max_words: int):
    best = None
    for s, e, kind in trigs:
        if e <= pos and kind in kinds:
            best = (s, e, kind)
    if best is None:
        return None
    between = sent[best[1]:pos]
    if _TERM.search(between) or len(between.split()) > max_words:
        return None
    return best


def _find_mentions(sent: str):
    raw = []
    for name, rx in _FORMAL_RX:
        for m in rx.finditer(sent):
            raw.append((m.start(), m.end(), [name], None))
    for m in _ABBR_RX.finditer(sent):
        raw.append((m.start(), m.end(), [_ABBR[m.group(1)]], None))
    for m in _MULTI_RX.finditer(sent):
        raw.append((m.start(), m.end(), list(MULTI_ABBR[m.group(1)]), None))
    for m in _IMPLIED_RX.finditer(sent):
        n, a = IMPLIED_NEGATION[m.group(1).lower()]
        raw.append((m.start(), m.end(), [n], a))
    
    for name, rx in _COLLOQUIAL_RX:
        for m in rx.finditer(sent):
            raw.append((m.start(), m.end(), [name], None))

    raw.sort(key=lambda t: (t[0], -(t[1] - t[0])))
    kept, last_end = [], -1
    for s, e, names, forced in raw:
        if s >= last_end:
            kept.append((s, e, names, forced))
            last_end = e
    return kept


def _last_words(text: str, n: int) -> str:
    return " ".join(text.split()[-n:])


def _first_words(text: str, n: int) -> str:
    return " ".join(text.split()[:n])


def _severity(name: str, pre: str, post: str) -> str:
    p = _last_words(pre, 3)
    if _SEVERE.search(p) or (name == "fever" and re.search(r"\bhigh\b", p, re.I)):
        return "severe"
    if _MODERATE.search(p):
        return "moderate"
    if _MILD.search(p):
        return "mild"
    m = _POST_SEV.match(post)
    if m:
        return {"severe": "severe", "moderate": "moderate", "mild": "mild"}[m.group(1).lower()]
    return "unspecified"


def _trend(pre: str, post: str) -> str:
    for text in (_last_words(pre, 3), _first_words(post, 6)):
        if _IMPROVE.search(text):
            return "improving"
        if _WORSEN.search(text):
            return "worsening"
        if _STABLE.search(text):
            return "stable"
    return "unknown"


def _durations(sent: str):
    out = []
    for m in _DUR1.finditer(sent):
        out.append((m.start(), m.end(), clean_duration(f"{m.group(1)} {m.group(2)}")))
    for m in _DUR2.finditer(sent):
        out.append((m.start(), m.end(), clean_duration(f"{m.group(1)} {m.group(2)}")))
    for m in _DUR3.finditer(sent):
        out.append((m.start(), m.end(), "1 day"))
    return out


def _is_chronic_duration(dur: Optional[str]) -> bool:
    if not dur:
        return False
    m = re.match(r"(\d+(?:\.\d+)?) (\w+)", dur)
    if not m:
        return False
    n, unit = float(m.group(1)), m.group(2)
    return unit.startswith("year") or (unit.startswith("month") and n >= 2) or (unit.startswith("week") and n >= 8)


_CONJ_ONLY = re.compile(r"^\s*(?:,|and|or|&|/|,\s*and|and/or|,\s*or)?\s*$", re.I)


# =========================================================================== main
def extract(text: str) -> Dict[str, List[Dict[str, Any]]]:
    symptoms: List[Dict[str, Any]] = []
    exposures: List[Dict[str, str]] = []

    for sent in (s.strip() for s in _SENT_SPLIT.split(text or "")):
        if not sent:
            continue
        trigs = _find_triggers(sent)
        mentions = _find_mentions(sent)
        durs = _durations(sent)

        # ----- assign durations to nearest mention, then share across "X and Y for 3 days"
        dur_of: Dict[int, str] = {}
        for ds, de, dval in durs:
            if not mentions:
                break
            idx = min(range(len(mentions)),
                      key=lambda i: min(abs(mentions[i][0] - de), abs(ds - mentions[i][1])))
            dur_of.setdefault(idx, dval)
        for i in range(1, len(mentions)):  # chain share (backward)
            if i in dur_of and (i - 1) not in dur_of and _CONJ_ONLY.match(sent[mentions[i - 1][1]:mentions[i][0]]):
                dur_of[i - 1] = dur_of[i]
        for i in range(len(mentions) - 2, -1, -1):  # chain share (forward)
            if i in dur_of and (i + 1) not in dur_of and _CONJ_ONLY.match(sent[mentions[i][1]:mentions[i + 1][0]]):
                dur_of[i + 1] = dur_of[i]

        for i, (s, e, names, forced) in enumerate(mentions):
            pre = sent[(mentions[i - 1][1] if i else 0):s]
            post = sent[e:(mentions[i + 1][0] if i + 1 < len(mentions) else len(sent))]

            # ---- assertion
            assertion = forced or "present"
            if not forced:
                t = _nearest(trigs, {"neg", "unc", "hyp"}, s, sent, 12)
                if t:
                    assertion = {"neg": "absent", "unc": "possible", "hyp": "hypothetical"}[t[2]]
                elif _POST_NEG.match(post):
                    assertion = "absent"
                elif _POST_UNC.match(post):
                    assertion = "possible"

            # ---- experiencer
            who, famhist = "patient", False
            t = _nearest(trigs, {"fam", "oth", "self", "famhist"}, s, sent, 14)
            if t:
                who = {"fam": "family", "oth": "other", "self": "patient", "famhist": "family"}[t[2]]
                famhist = t[2] == "famhist"

            # ---- temporality
            time = "current"
            if _nearest(trigs, {"past"}, s, sent, 6) or _POST_PAST.match(post) or _PRE_PAST.search(pre) or famhist:
                time = "past"
            elif _nearest(trigs, {"chronic"}, s, sent, 4) or _POST_CHRONIC.match(post):
                time = "chronic"

            severity = _severity(names[0], pre, post)
            trend = _trend(pre, post)
            duration = dur_of.get(i)
            if assertion in ("absent", "hypothetical"):
                time, severity, trend, duration = "current", "unspecified", "unknown", None
            elif time == "current" and _is_chronic_duration(duration):
                time = "chronic"

            for n in names:
                symptoms.append(new_symptom(n, assertion, time, who, severity, trend, duration))

        # ----- exposures (same negation/uncertainty scope logic)
        for etype, rx in _EXPOSURE_RX:
            for m in rx.finditer(sent):
                t = _nearest(trigs, {"neg", "unc", "hyp"}, m.start(), sent, 12)
                a = {"neg": "absent", "unc": "possible", "hyp": None}.get(t[2], "present") if t else "present"
                if a:
                    exposures.append({"type": etype, "assertion": a})

    # ----- vital-sign derived symptoms
    have = {s["name"] for s in symptoms}
    if text:
        m = _TEMP_RX.search(text)
        if m and "fever" not in have:
            val, unit = float(m.group(1)), (m.group(2) or "").upper()
            celsius = unit == "C" or (not unit and val < 45)
            if (celsius and 38.0 <= val < 45) or (not celsius and 100.4 <= val < 112):
                symptoms.append(new_symptom("fever", severity="severe" if (val >= 39.4 if celsius else val >= 103) else "unspecified"))
        m = _SPO2_RX.search(text)
        if m and "low_oxygen" not in have and 50 <= float(m.group(1)) <= 91:
            symptoms.append(new_symptom("low_oxygen"))

    return _finalize(symptoms, exposures)


def _finalize(symptoms, exposures):
    merged: Dict[tuple, Dict[str, Any]] = {}
    for s in symptoms:
        key = (s["name"], s["assertion"], s["who"], s["time"])
        if key not in merged:
            merged[key] = dict(s)
            continue
        cur = merged[key]
        for f, empty in (("severity", "unspecified"), ("trend", "unknown"), ("duration", None)):
            if cur[f] == empty and s[f] != empty:
                cur[f] = s[f]
    ex, seen = [], set()
    for e in exposures:
        k = (e["type"], e["assertion"])
        if k not in seen:
            seen.add(k)
            ex.append(e)
    symptoms_out = list(merged.values())
    return {"symptoms": symptoms_out, "exposures": infer_exposures(symptoms_out, ex)}


class RuleExtractor:
    """Object wrapper so rule and SLM backends share the same interface."""

    name = "rule"

    def extract(self, text: str) -> Dict[str, Any]:
        return extract(text)
