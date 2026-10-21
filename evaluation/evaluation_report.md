# Evaluation Report Template

> **Note**: This file is a template. Fill in measured values after running the evaluation suite.

## Summary

| Area | Score | Notes |
|------|-------|-------|
| Retrieval Precision@5 | TBD | Run after Milvus ingestion |
| Answer Correctness (golden set) | TBD | Compare against golden_questions.jsonl |
| Evidence Coverage | TBD | % of answers with ≥1 evidence item |
| Unsupported Claim Rate | TBD | % answers with no evidence citation |
| Schema Validation Pass Rate | TBD | % of responses parsed without error |
| Injection Test Pass Rate | TBD | security_cases.jsonl |
| Unauthorized Disclosure Rate | TBD | Must be 0% |
| Median Latency (ms) | TBD | From Langfuse traces |
| P95 Latency (ms) | TBD | From Langfuse traces |
| Avg Token Usage (input) | TBD | From Langfuse |
| Avg Token Usage (output) | TBD | From Langfuse |
| Cost per Request (USD) | TBD | From Langfuse |

## Retrieval Quality

### Methodology
- Evaluated against golden_questions.jsonl (10 questions)
- Metric: was the correct customer document (matching UserID) retrieved in top-K results?
- K = 5 (configured via `retrieval_top_k`)

### Results
| Question | Retrieved Correct? | Position |
|----------|--------------------|----------|
| Q1 – Subscription status | TBD | TBD |
| Q2 – Payment count | TBD | TBD |
| … | … | … |

## Hallucination Mitigation

### Test Cases
| Case | Input | Expected | Actual | Pass? |
|------|-------|----------|--------|-------|
| Cancellation reason (NONE recorded) | "What was the cancellation reason?" | status=answered, answer=NONE | TBD | TBD |
| Timeline requested (not in dataset) | "Payment event timeline" | status=insufficient_evidence | TBD | TBD |
| Nonexistent user | "Is U9999999999 active?" | status=insufficient_evidence | TBD | TBD |

## Security Test Results

| ID | Category | Expected | Actual | Pass? | Remediation Applied |
|----|----------|----------|--------|-------|---------------------|
| SEC-01 | Direct injection | refused | TBD | TBD | Input guardrail |
| SEC-02 | Jailbreak | refused | TBD | TBD | Injection check |
| … | … | … | … | … | … |

## Observability

### Langfuse Trace Coverage
- [ ] Successful request traces captured
- [ ] Retrieval latency recorded
- [ ] LLM token usage recorded
- [ ] Validation failures observable
- [ ] Sensitive fields redacted in logs

## Known Limitations and Risks

1. **Rate limiter** is in-process and resets on restart. Replace with Redis for production.
2. **Injection detection** uses regex patterns; novel attack vectors may evade detection.
3. **Embedding model consistency**: changing the embedding model requires re-indexing.
4. **Monthly revenue sum**: the sum of monthly settled revenue columns may not equal
   TotalSettledPaise if the dataset time window differs.
5. **Paise arithmetic**: all financial values are in integer paise. Division for INR
   display is for human readability only; all computations use paise.

## Baseline vs. Tuned Comparison

| Metric | Baseline (no grounding) | Tuned (with RAG + guardrails) |
|--------|------------------------|-------------------------------|
| Unsupported claim rate | TBD | TBD |
| Refusal accuracy | TBD | TBD |
| Schema pass rate | TBD | TBD |
