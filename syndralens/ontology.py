
# ----------------------------------------------------------------------------
# Controlled vocabularies for the structured output
# ----------------------------------------------------------------------------
ASSERTIONS = ["present", "absent", "possible", "hypothetical"]
TIMES = ["current", "past", "chronic"]
WHO = ["patient", "family", "other"]
SEVERITIES = ["mild", "moderate", "severe", "unspecified"]
TRENDS = ["worsening", "improving", "stable", "unknown"]
SIGNAL_LEVELS = ["none", "weak", "moderate", "strong"]

# ----------------------------------------------------------------------------
# Symptom lexicon
# ----------------------------------------------------------------------------
SYMPTOMS = {
    "fever": {
        "formal": [
            "fever",
            "fevers",
            "febrile",
            "pyrexia",
            "high temperature",
            "elevated temperature",
            "subjective fever",
            "low-grade temperature",
            "low grade fever",
        ],
        "abbr": [],
        "colloquial": [
            "burning up",
            "running a temperature",
            "feeling feverish",
            "body feels hot",
            "high temp",
        ],
    },
    "chills": {
        "formal": ["chills", "rigors", "shivering"],
        "abbr": [],
        "colloquial": ["shaking chills", "feeling cold and shivery"],
    },
    "cough": {
        "formal": [
            "cough",
            "coughing",
            "coughs",
            "productive cough",
            "dry cough",
            "hacking cough",
        ],
        "abbr": [],
        "colloquial": [
            "hacking away",
            "can't stop coughing",
            "persistent hacking",
        ],
    },
    "dyspnea": {
        "formal": [
            "shortness of breath",
            "short of breath",
            "dyspnea",
            "dyspnoea",
            "breathlessness",
            "breathless",
            "difficulty breathing",
            "breathing difficulty",
            "difficulty in breathing",
            "trouble breathing",
            "labored breathing",
            "respiratory distress",
        ],
        "abbr": ["SOB", "DOE"],
        "colloquial": [
            "can't catch my breath",
            "struggling to breathe",
            "gasping for air",
            "winded",
        ],
    },
    "sore_throat": {
        "formal": ["sore throat", "throat pain", "pharyngitis", "odynophagia"],
        "abbr": [],
        "colloquial": [
            "scratchy throat",
            "throat hurts",
            "painful swallowing",
        ],
    },
    "rhinorrhea": {
        "formal": [
            "runny nose",
            "rhinorrhea",
            "rhinorrhoea",
            "nasal congestion",
            "stuffy nose",
            "coryza",
            "nasal discharge",
        ],
        "abbr": [],
        "colloquial": ["blocked nose", "sniffles", "nose running"],
    },
    "wheeze": {
        "formal": ["wheeze", "wheezing", "wheezes"],
        "abbr": [],
        "colloquial": ["whistling sound when breathing", "chest whistling"],
    },
    "low_oxygen": {
        "formal": [
            "hypoxia",
            "hypoxemia",
            "low oxygen",
            "oxygen desaturation",
            "desaturation",
            "low o2 sat",
        ],
        "abbr": [],
        "colloquial": ["oxygen levels dropped", "low oxygen reading"],
    },
    "hemoptysis": {
        "formal": ["hemoptysis", "coughing up blood", "blood-tinged sputum"],
        "abbr": [],
        "colloquial": ["spitting blood", "blood in phlegm"],
    },
    "chest_pain": {
        "formal": ["chest pain", "chest tightness", "chest discomfort"],
        "abbr": ["CP"],
        "colloquial": ["pressure in the chest", "tight chest"],
    },
    "diarrhea": {
        "formal": [
            "diarrhea",
            "diarrhoea",
            "loose stools",
            "loose stool",
            "watery stools",
            "frequent stools",
            "loose motions",
        ],
        "abbr": [],
        "colloquial": [
            "running to the toilet",
            "runny stools",
            "watery motions",
        ],
    },
    "vomiting": {
        "formal": ["vomiting", "vomit", "vomited", "emesis"],
        "abbr": [],
        "colloquial": ["throwing up", "keeps being sick", "puking"],
    },
    "nausea": {
        "formal": ["nausea", "nauseated", "nauseous", "queasy"],
        "abbr": [],
        "colloquial": ["feeling sick to the stomach", "queasy stomach"],
    },
    "abdominal_pain": {
        "formal": [
            "abdominal pain",
            "abd pain",
            "stomach pain",
            "belly pain",
            "stomach ache",
            "abdominal cramps",
            "stomach cramps",
            "epigastric pain",
            "abdominal cramping",
        ],
        "abbr": [],
        "colloquial": ["tummy ache", "cramps in the belly", "belly hurts"],
    },
    "rash": {
        "formal": [
            "rash",
            "rashes",
            "skin eruption",
            "maculopapular rash",
            "vesicular rash",
            "petechiae",
            "skin lesions",
        ],
        "abbr": [],
        "colloquial": [
            "red spots all over",
            "spots on the skin",
            "itchy red patches",
            "blisters on the skin",
        ],
    },
    "headache": {
        "formal": ["headache", "headaches", "head pain"],
        "abbr": ["HA"],
        "colloquial": ["head is pounding", "splitting head"],
    },
    "neck_stiffness": {
        "formal": [
            "neck stiffness",
            "stiff neck",
            "nuchal rigidity",
            "neck rigidity",
            "meningismus",
        ],
        "abbr": [],
        "colloquial": ["can't bend the neck", "neck feels locked"],
    },
    "altered_mental_status": {
        "formal": [
            "altered mental status",
            "confusion",
            "confused",
            "disoriented",
            "disorientation",
            "lethargy",
            "lethargic",
            "somnolent",
            "unresponsive",
        ],
        "abbr": ["AMS"],
        "colloquial": ["not making sense", "very drowsy and hard to wake"],
    },
    "seizure": {
        "formal": [
            "seizure",
            "seizures",
            "convulsion",
            "convulsions",
            "seizing",
        ],
        "abbr": [],
        "colloquial": ["fits", "shaking episode with loss of awareness"],
    },
    "myalgia": {
        "formal": [
            "myalgia",
            "myalgias",
            "muscle pain",
            "muscle aches",
            "body ache",
            "body aches",
            "body pain",
        ],
        "abbr": [],
        "colloquial": ["whole body aching", "aching all over"],
    },
    "neck_pain": {
        "formal": ["neck pain"],
        "abbr": ["cervicalgia"],
        "colloquial": [
            "pain in the neck",
            "neck ache",
            "sore neck",
        ],
    },
    "fatigue": {
        "formal": [
            "fatigue",
            "fatigued",
            "tiredness",
            "malaise",
            "generalized weakness",
        ],
        "abbr": [],
        "colloquial": ["wiped out", "completely exhausted", "no energy"],
    },
    "jaundice": {
        "formal": [
            "jaundice",
            "jaundiced",
            "icterus",
            "scleral icterus",
            "yellowing of the skin",
            "yellow eyes",
        ],
        "abbr": [],
        "colloquial": ["eyes turned yellow", "skin looks yellow"],
    },
    "conjunctivitis": {
        "formal": [
            "conjunctivitis",
            "red eyes",
            "pink eye",
            "eye redness",
            "conjunctival injection",
        ],
        "abbr": [],
        "colloquial": ["bloodshot watery eyes"],
    },
    "joint_pain": {
        "formal": [
            "joint pain",
            "joint pains",
            "arthralgia",
            "arthralgias",
            "painful joints",
        ],
        "abbr": [],
        "colloquial": ["aching joints", "joints hurt"],
    },
    "bleeding": {
        "formal": [
            "bleeding",
            "hemorrhage",
            "haemorrhage",
            "bleeding gums",
            "nosebleed",
            "epistaxis",
            "hematemesis",
            "melena",
            "blood in stool",
            "easy bruising",
        ],
        "abbr": [],
        "colloquial": [
            "gums bleeding",
            "bruising very easily",
            "nose keeps bleeding",
        ],
    },
    "anosmia": {
        "formal": ["anosmia", "loss of smell", "loss of taste", "ageusia"],
        "abbr": [],
        "colloquial": ["can't smell anything", "food has no taste"],
    },
}

# Multi-symptom abbreviations (case-sensitive)
MULTI_ABBR = {
    "N/V/D": ["nausea", "vomiting", "diarrhea"],
    "N/V": ["nausea", "vomiting"],
}

# Surface forms that already carry negation
IMPLIED_NEGATION = {
    "afebrile": ("fever", "absent"),
    "non-febrile": ("fever", "absent"),
    "nonfebrile": ("fever", "absent"),
}

# ----------------------------------------------------------------------------
# Exposures
# ----------------------------------------------------------------------------
EXPOSURES = [
    "sick_contact",
    "travel",
    "animal_contact",
    "healthcare_contact",
    "food_water",
    "vector",
]
EXPOSURE_ASSERTIONS = ["present", "absent", "possible"]

# ----------------------------------------------------------------------------
# Level-3: syndrome definitions
# ----------------------------------------------------------------------------
SYNDROMES = {
    "respiratory": {
        "weights": {
            "cough": 0.8,
            "dyspnea": 1.0,
            "wheeze": 0.8,
            "low_oxygen": 1.2,
            "hemoptysis": 0.8,
            "sore_throat": 0.4,
            "rhinorrhea": 0.4,
            "fever": 0.5,
        },
        "require": [{"cough", "dyspnea", "wheeze", "low_oxygen", "hemoptysis"}],
    },
    "influenza_like": {
        "weights": {
            "fever": 1.0,
            "cough": 0.8,
            "sore_throat": 0.6,
            "myalgia": 0.6,
            "fatigue": 0.3,
            "chills": 0.3,
            "headache": 0.3,
            "rhinorrhea": 0.2,
        },
        "require": [{"fever"}, {"cough", "sore_throat"}],
    },
    "gastrointestinal": {
        "weights": {
            "diarrhea": 1.0,
            "vomiting": 0.8,
            "nausea": 0.4,
            "abdominal_pain": 0.5,
            "fever": 0.3,
        },
        "require": [{"diarrhea", "vomiting"}],
    },
    "febrile_rash": {
        "weights": {
            "fever": 1.0,
            "rash": 1.2,
            "conjunctivitis": 0.3,
            "joint_pain": 0.4,
            "myalgia": 0.2,
        },
        "require": [{"fever"}, {"rash"}],
    },
    "neurological": {
        "weights": {
            "neck_stiffness": 1.2,
            "altered_mental_status": 1.2,
            "seizure": 1.2,
            "headache": 0.5,
            "fever": 0.5,
        },
        "require": [{"neck_stiffness", "altered_mental_status", "seizure"}],
    },
    "hemorrhagic_febrile": {
        "weights": {
            "fever": 1.0,
            "bleeding": 1.4,
            "myalgia": 0.2,
            "headache": 0.2,
        },
        "require": [{"fever"}, {"bleeding"}],
    },
    "acute_jaundice": {
        "weights": {
            "jaundice": 1.4,
            "fever": 0.3,
            "vomiting": 0.2,
            "abdominal_pain": 0.2,
        },
        "require": [{"jaundice"}],
    },
    "febrile_nonspecific": {
        "weights": {
            "fever": 1.0,
            "chills": 0.3,
            "myalgia": 0.2,
            "fatigue": 0.2,
            "headache": 0.2,
        },
        "require": [{"fever"}],
    },
}

SIGNAL_THRESHOLDS = {"weak": 1.0, "moderate": 2.0, "strong": 3.0}

ASSERTION_WEIGHT = {
    "present": 1.0,
    "possible": 0.5,
    "absent": 0.0,
    "hypothetical": 0.0,
}
TIME_WEIGHT = {"current": 1.0, "chronic": 0.3, "past": 0.0}
SEVERITY_WEIGHT = {
    "mild": 0.9,
    "moderate": 1.0,
    "severe": 1.2,
    "unspecified": 1.0,
}
TREND_WEIGHT = {
    "worsening": 1.15,
    "improving": 0.85,
    "stable": 1.0,
    "unknown": 1.0,
}

# ----------------------------------------------------------------------------
# Safety guardrail
# ----------------------------------------------------------------------------
FORBIDDEN_TERMS = [
    "novel pathogen",
    "new pathogen",
    "pathogen detected",
    "outbreak confirmed",
    "confirmed outbreak",
    "pandemic",
    "bioterror",
    "bioweapon",
    "covid",
    "sars",
    "ebola",
    "influenza confirmed",
    "diagnosis:",
    "diagnosed with",
]

DISCLAIMER = (
    "Syndromic signal only. Not a diagnosis, not a pathogen identification, "
    "and not a confirmed outbreak."
)