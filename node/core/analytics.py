from collections import Counter, defaultdict
from itertools import combinations

from node.core.matching import MLMatcher


def symptom_names(record):
    return sorted(item.symptom.symptom_name for item in record.record_symptoms)


def disease_hotspots(records):
    """Group repeated disease/symptom patterns by hospital for hotspot detection."""
    hotspots = defaultdict(lambda: {"case_count": 0, "hospitals": set(), "symptoms": Counter()})
    for record in records:
        disease = record.diagnosis.disease_name if record.diagnosis else "Undiagnosed"
        bucket = hotspots[disease]
        bucket["case_count"] += 1
        bucket["hospitals"].add(record.hospital.name if record.hospital else "Unknown")
        bucket["symptoms"].update(symptom_names(record))

    return [
        {
            "disease_name": disease,
            "case_count": data["case_count"],
            "hospitals": sorted(data["hospitals"]),
            "top_symptoms": [name for name, _ in data["symptoms"].most_common(5)],
            "alert": "WATCHLIST" if data["case_count"] >= 2 else "NORMAL",
        }
        for disease, data in sorted(hotspots.items(), key=lambda item: item[1]["case_count"], reverse=True)
    ]


def symptom_evolution(records):
    """Create a date-wise symptom timeline from available clinical records."""
    timeline = []
    for record in sorted(records, key=lambda item: item.record_date or ""):
        timeline.append(
            {
                "record_id": record.id,
                "date": record.record_date.isoformat() if record.record_date else None,
                "hospital_name": record.hospital.name if record.hospital else "Unknown",
                "diagnosis": record.diagnosis.disease_name if record.diagnosis else "Undiagnosed",
                "symptoms": [
                    {"name": item.symptom.symptom_name, "severity": item.severity}
                    for item in sorted(record.record_symptoms, key=lambda value: value.symptom.symptom_name)
                ],
            }
        )
    return timeline


def duplicate_cases(records, threshold=0.75):
    """Detect records with very similar symptom sets using Jaccard similarity."""
    duplicates = []
    for left, right in combinations(records, 2):
        left_set = set(symptom_names(left))
        right_set = set(symptom_names(right))
        if not left_set or not right_set:
            continue
        score = len(left_set & right_set) / len(left_set | right_set)
        if score >= threshold:
            duplicates.append(
                {
                    "record_a": left.id,
                    "record_b": right.id,
                    "similarity": round(score, 3),
                    "shared_symptoms": sorted(left_set & right_set),
                    "alert": "Possible duplicate clinical case",
                }
            )
    return duplicates


def rare_patterns(records):
    """Flag records containing uncommon symptom combinations."""
    symptom_frequency = Counter()
    for record in records:
        symptom_frequency.update(symptom_names(record))

    patterns = []
    for record in records:
        symptoms = symptom_names(record)
        rare_symptoms = [name for name in symptoms if symptom_frequency[name] == 1]
        if len(rare_symptoms) >= 2:
            patterns.append(
                {
                    "record_id": record.id,
                    "disease_name": record.diagnosis.disease_name if record.diagnosis else "Undiagnosed",
                    "rare_symptoms": rare_symptoms,
                    "reason": "Uncommon symptom combination in local database",
                }
            )
    return patterns


def emergency_alerts(records):
    alerts = []
    for record in records:
        severe = [item for item in record.record_symptoms if item.severity and item.severity >= 5]
        if len(severe) >= 2:
            alerts.append(
                {
                    "record_id": record.id,
                    "disease_name": record.diagnosis.disease_name if record.diagnosis else "Undiagnosed",
                    "risk_alert": "CRITICAL",
                    "critical_symptoms": [item.symptom.symptom_name for item in severe],
                }
            )
    return alerts


def explain_record_similarity(records, symptoms):
    matcher = MLMatcher(records)
    return matcher.find_matches(symptoms, top_k=5)
