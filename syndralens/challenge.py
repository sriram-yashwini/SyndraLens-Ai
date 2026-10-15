
P, A, Q, H = "present", "absent", "possible", "hypothetical"
PT, FM, OT = "patient", "family", "other"
CU, PA, CH = "current", "past", "chronic"

CHALLENGE = [
    ("45 yo M c/o fever and cough x 3 days, worsening SOB. Denies chest pain.",
     {("fever", P, PT, CU), ("cough", P, PT, CU), ("dyspnea", P, PT, CU), ("chest_pain", A, PT, CU)}),
    ("Patient denies fever, cough or sore throat but reports headache.",
     {("fever", A, PT, CU), ("cough", A, PT, CU), ("sore_throat", A, PT, CU), ("headache", P, PT, CU)}),
    ("Her husband has fever and body aches. She has no symptoms at present.",
     {("fever", P, FM, CU), ("myalgia", P, FM, CU)}),
    ("Cough with increasing frequency over the past 5 days; afebrile.",
     {("cough", P, PT, CU), ("fever", A, PT, CU)}),
    ("Possible pneumonia, cannot rule out hypoxia. Reports wheezing.",
     {("low_oxygen", Q, PT, CU), ("wheeze", P, PT, CU)}),
    ("History of asthma with wheezing last year, resolved. Currently no wheezing.",
     {("wheeze", A, PT, CU), ("wheeze", P, PT, PA)}),
    ("Chronic cough for years, baseline unchanged.",
     {("cough", P, PT, CH)}),
    ("Return to the ED if fever or shortness of breath develops.",
     {("fever", H, PT, CU), ("dyspnea", H, PT, CU)}),
    ("Triage: Temp 101.8 F, SpO2 88%. Chief complaint: abd pain.",
     {("fever", P, PT, CU), ("low_oxygen", P, PT, CU), ("abdominal_pain", P, PT, CU)}),
    ("N/V/D since yesterday after eating at a restaurant. No fever.",
     {("nausea", P, PT, CU), ("vomiting", P, PT, CU), ("diarrhea", P, PT, CU), ("fever", A, PT, CU)}),
    ("Severe headache with neck stiffness and one episode of confusion.",
     {("headache", P, PT, CU), ("neck_stiffness", P, PT, CU), ("altered_mental_status", P, PT, CU)}),
    ("Fever without cough. Mother brought the patient in.",
     {("fever", P, PT, CU), ("cough", A, PT, CU)}),
    ("Fever with rash for 2 days; his coworker has the same rash.",
     {("fever", P, PT, CU), ("rash", P, PT, CU), ("rash", P, OT, CU)}),
    ("?fever, no chills. Mild cough.",
     {("fever", Q, PT, CU), ("chills", A, PT, CU), ("cough", P, PT, CU)}),
    ("Jaundice noted yesterday, eyes yellow and dark urine. Denies sick contacts.",
     {("jaundice", P, PT, CU)}),
    ("Pt reports sore throat and runny nose; no fever but wife is coughing.",
     {("sore_throat", P, PT, CU), ("rhinorrhea", P, PT, CU), ("fever", A, PT, CU), ("cough", P, FM, CU)}),
]
