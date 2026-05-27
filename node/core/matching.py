from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from node.core.clinical_knowledge import (
    DISEASE_PROFILES,
    EMERGENCY_SYMPTOMS,
    MILD_COMMON_SYMPTOMS,
)

# Simple synonym handling keeps the demo understandable while still making the
# matching feel realistic during viva/demo queries.
SYNONYM_DICT = {
    "high temperature": "fever",
    "temperature": "fever",
    "pyrexia": "fever",
    "renal problem": "kidney issue",
    "kidney problem": "kidney issue",
    "tiredness": "fatigue",
    "weakness": "fatigue",
    "skin rash": "rash",
    "fit": "seizures",
    "fits": "seizures",
    "convulsions": "seizures",
    "small head": "microcephaly",
    "development delay": "developmental delay",
    "body pain": "body ache",
    "myalgia": "body ache",
    "cold": "common cold",
    "running nose": "runny nose",
    "breathing difficulty": "shortness of breath",
    "breathlessness": "shortness of breath",
    "fits": "seizures",
    "low platelets": "low platelet count",
    "platelets low": "low platelet count",
    "stomach pain": "abdominal pain",
    "loose stools": "diarrhea",
    "loose motion": "diarrhea",
    "vomit": "vomiting",
    "light sensitive": "light sensitivity",
    "high fever": "fever",
    "muscle pain": "body ache",
    "poor feeding": "feeding difficulty",
    "delayed milestones": "developmental delay",
    "motor delay": "developmental delay",
    "hand flapping": "hand wringing",
    "red eye": "conjunctivitis",
    "red eyes": "conjunctivitis",
    "coughing blood": "blood in sputum",
    "chronic cough": "persistent cough",
    "burning feet": "burning pain",
    "albuminuria": "proteinuria",
    "photosensitive rash": "photosensitivity",
}

def normalize_symptoms(symptoms_list):
    """Normalizes symptoms using a synonym dictionary."""
    normalized = []
    for s in symptoms_list:
        clean_s = s.lower().strip()
        value = SYNONYM_DICT.get(clean_s, clean_s)
        if value and value not in normalized:
            normalized.append(value)
    return normalized

def _normalized_severity(severity):
    values = {}
    for symptom, score in (severity or {}).items():
        key = SYNONYM_DICT.get(symptom.lower().strip(), symptom.lower().strip())
        values[key] = max(1, min(int(score or 1), 5))
    return values

def _risk_alert(score, matched_count, rare_probability, max_severity=0, emergency_count=0):
    if (max_severity >= 5 and matched_count >= 2) or emergency_count >= 2:
        return "CRITICAL"
    if max_severity <= 2 and emergency_count == 0 and matched_count <= 1:
        return "LOW"
    if score >= 0.62 or matched_count >= 3 or rare_probability >= 0.75 or emergency_count == 1:
        return "HIGH"
    if score >= 0.30 or matched_count >= 2:
        return "MEDIUM"
    return "LOW"

def _profile_for(record):
    name = record.diagnosis.disease_name if record.diagnosis else "Undiagnosed"
    return DISEASE_PROFILES.get(name, {"rarity": "rare", "category": "uncategorized", "hallmarks": set(), "age_group": "all"})

def _note_bonus(notes, profile):
    if not notes:
        return 0.0
    note_text = notes.lower()
    bonus_terms = set(profile.get("hallmarks", set()))
    bonus_terms.update(["family history", "progressive", "recurrent", "developmental regression", "travel", "exposure"])
    return min(0.14, sum(0.025 for term in bonus_terms if term in note_text))

def _infer_age_group(text):
    if not text:
        return None
    value = text.lower()
    pediatric_terms = {"infant", "baby", "child", "pediatric", "toddler", "newborn", "school age"}
    adult_terms = {"adult", "elderly", "middle aged", "middle-aged"}
    if any(term in value for term in pediatric_terms):
        return "pediatric"
    if any(term in value for term in adult_terms):
        return "adult"
    return None

def _age_group_score(inferred, profile_group):
    if not inferred or profile_group in {"all", "child_adult", "teen_adult"}:
        return 0.0
    if inferred == profile_group:
        return 0.04
    return -0.08

class MLMatcher:
    """
    Advanced Machine Learning Pipeline for Distributed Rare Disease Matching.
    Uses TF-IDF Vectorization and Cosine Similarity.
    """
    def __init__(self, records):
        self.records = records
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.corpus = []
        
        # Build the corpus from records
        for r in records:
            doc_parts = []
            
            profile = _profile_for(r)

            # 1. Weighted Symptom Matching with clinical profile enrichment.
            for rs in r.record_symptoms:
                sym_name = rs.symptom.symptom_name.lower()
                severity = rs.severity if rs.severity else 1
                doc_parts.extend([sym_name] * severity)
            doc_parts.extend(list(profile.get("hallmarks", set())) * 2)
            doc_parts.append(profile.get("category", ""))
            doc_parts.append(profile.get("age_group", ""))
            
            # 2. Diagnosis Keywords
            if r.diagnosis:
                doc_parts.append(r.diagnosis.disease_name.lower())
            
            # 3. Clinical Notes
            if r.notes:
                doc_parts.append(r.notes.lower())
                
            self.corpus.append(" ".join(doc_parts))
            
        # Fit the TF-IDF model on the clinical corpus
        if self.corpus:
            self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)
            
    def find_matches(self, query_symptoms, top_k=3, severity=None, notes=None):
        """Finds calibrated matches using TF-IDF plus clinical risk rules."""
        if not self.corpus:
            return []
            
        # Handle synonyms for incoming query
        norm_symptoms = normalize_symptoms(query_symptoms)
        severity = _normalized_severity(severity)
        weighted_terms = []
        for symptom in norm_symptoms:
            weight = severity.get(symptom, 1)
            weighted_terms.extend([symptom] * weight)
        if notes:
            weighted_terms.append(notes.lower())
        query_str = " ".join(weighted_terms)
        
        # Vectorize query
        query_vec = self.vectorizer.transform([query_str])
        
        # Compute Cosine Similarity between query and all records
        cosine_sim = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        query_set = set(norm_symptoms)
        max_severity = max([severity.get(s, 1) for s in norm_symptoms] or [1])
        mild_query = max_severity <= 2 and query_set and query_set.issubset(MILD_COMMON_SYMPTOMS)
        severe_specific_count = len([sym for sym in query_set if severity.get(sym, 1) >= 4 and sym not in MILD_COMMON_SYMPTOMS])
        inferred_age = _infer_age_group(notes)

        candidates = []
        for idx, record in enumerate(self.records):
            base_score = float(cosine_sim[idx])
            profile = _profile_for(record)
            rarity = profile.get("rarity", "rare")
            diagnosis_name = record.diagnosis.disease_name if record.diagnosis else "Undiagnosed"
            record_symptoms = {rs.symptom.symptom_name.lower(): rs.severity or 1 for rs in record.record_symptoms}
            hallmark_matches = query_set.intersection(set(profile.get("hallmarks", set())))
            direct_matches = query_set.intersection(set(record_symptoms))
            matched_syms = sorted(direct_matches.union(hallmark_matches))
            weighted_overlap = sum(min(severity.get(sym, 1), record_symptoms.get(sym, 1)) / 5 for sym in direct_matches)
            symptom_score = min(0.34, (0.09 * len(direct_matches)) + (0.05 * len(hallmark_matches)) + (0.06 * weighted_overlap))
            note_score = _note_bonus(notes, profile)
            age_score = _age_group_score(inferred_age, profile.get("age_group", "all"))
            emergency_count = len(query_set.intersection(EMERGENCY_SYMPTOMS))
            severity_score = 0.03 * max(0, max_severity - 2)
            disease_name_score = 0.10 if diagnosis_name.lower() in query_set else 0.0

            calibrated = (base_score * 0.50) + symptom_score + note_score + age_score + severity_score + disease_name_score
            rare_gate = len(matched_syms) >= 3 or (len(matched_syms) >= 2 and (max_severity >= 3 or base_score >= 0.20))
            if rarity == "rare":
                calibrated -= 0.18
                if mild_query:
                    calibrated -= 0.22
                if not rare_gate:
                    calibrated -= 0.18
            else:
                calibrated += 0.12
                if mild_query:
                    calibrated += 0.12
                if severe_specific_count >= 2 and len(direct_matches) < 2 and disease_name_score == 0:
                    calibrated -= 0.20

            threshold = 0.24 if rarity == "common" else 0.38
            if calibrated < threshold:
                continue

            rare_prob = 0.08 if rarity == "common" else 0.28
            rare_prob += 0.12 * len(hallmark_matches) + 0.08 * max(0, max_severity - 2) + (0.08 if note_score >= 0.05 else 0)
            if mild_query:
                rare_prob -= 0.18
            if rarity == "common":
                rare_prob = min(rare_prob, 0.22)
            rare_prob = round(max(0.03, min(rare_prob, 0.94)), 2)
            confidence = max(0.05, min(calibrated, 0.92))

            reasons = []
            if matched_syms:
                reasons.append(f"shared symptoms: {', '.join(s.title() for s in matched_syms)}")
            if note_score:
                reasons.append("clinical notes support the disease pattern")
            if rarity == "rare" and not mild_query:
                reasons.append("rare-disease gate passed through correlated symptom evidence")
            if rarity == "common" and mild_query:
                reasons.append("mild common symptom pattern favors common disease first")
            explanation = "Matched because " + "; ".join(reasons) + "." if reasons else "Matched through clinical text similarity."

            candidates.append({
                "record_id": record.id,
                "hospital_name": record.hospital.name if record.hospital else "Unknown",
                "disease_name": diagnosis_name,
                "similarity_score": round(confidence, 3),
                "confidence_score": f"{round(confidence * 100, 1)}%",
                "explanation": explanation,
                "matched_symptoms": [s.title() for s in matched_syms],
                "disease_classification": rarity,
                "confidence_breakdown": {
                    "tfidf": round(base_score, 3),
                    "symptom_overlap": round(symptom_score, 3),
                    "notes": round(note_score, 3),
                    "severity": round(severity_score, 3),
                    "age_context": round(age_score, 3),
                    "disease_name": round(disease_name_score, 3),
                },
                "rare_disease_probability": rare_prob,
                "risk_alert": _risk_alert(confidence, len(matched_syms), rare_prob, max_severity, emergency_count),
                "age_at_encounter": record.age_at_encounter,
                "record_date": record.record_date.isoformat() if record.record_date else None,
                "_dedupe_key": diagnosis_name,
            })

        candidates.sort(key=lambda item: item["similarity_score"], reverse=True)
        results = []
        seen_diagnoses = set()
        for candidate in candidates:
            key = candidate.pop("_dedupe_key")
            if key in seen_diagnoses:
                continue
            seen_diagnoses.add(key)
            results.append(candidate)
            if len(results) >= top_k:
                break
        return results
