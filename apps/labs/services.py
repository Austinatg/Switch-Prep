import re

def evaluate_submission(lab, answer):
    """Safe deterministic checks only. Never executes learner-submitted code or SQL."""
    submitted=(answer or "").strip()
    if lab.evaluation_type == "review":
        return {"status":"needs_review","score":0,"feedback":"Your work has been submitted for instructor review.","details":{"mode":"manual_review"}}
    if lab.evaluation_type == "exact":
        norm=lambda value: re.sub(r"\s+", " ", value or "").strip().casefold()
        passed=bool(lab.expected_output.strip()) and norm(submitted)==norm(lab.expected_output)
        return {"status":"passed" if passed else "submitted","score":100 if passed else 0,"feedback":"Correct output. Great work!" if passed else "The output does not match the expected result yet. Review the task and try again.","details":{"mode":"exact_output","matched":passed}}
    required=[str(x).casefold() for x in (lab.required_keywords or []) if str(x).strip()]
    found=[word for word in required if word in submitted.casefold()]
    score=round(100*len(found)/len(required)) if required else 0
    passed=bool(required) and len(found)==len(required)
    return {"status":"passed" if passed else "submitted","score":score,"feedback":"All required elements are present." if passed else f"Found {len(found)} of {len(required)} required elements.","details":{"mode":"keywords","found":found,"missing":[x for x in required if x not in found]}}
