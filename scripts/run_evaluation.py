"""
scripts/run_evaluation.py
Command-line evaluation runner for RewardSphere AI RAG agent.
Evaluates golden questions and security test cases against the live FastAPI backend.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
import requests

ROOT_DIR = Path(__file__).resolve().parent.parent
EVAL_DIR = ROOT_DIR / "evaluation"


def load_jsonl(path: Path) -> list[dict]:
    results = []
    if not path.exists():
        print(f"Error: {path} not found.")
        return results
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def evaluate_golden_case(case: dict, base_url: str) -> dict:
    start = time.time()
    try:
        resp = requests.post(
            f"{base_url}/chat",
            json={"question": case["question"], "user_id": case["user_id"]},
            timeout=90,
        )
        elapsed = round((time.time() - start) * 1000)
        if resp.status_code != 200:
            try:
                detail = resp.json().get("detail", f"HTTP {resp.status_code}")
                if isinstance(detail, list):
                    detail = json.dumps(detail)
            except Exception:
                detail = resp.text
            return {
                **case,
                "passed": False,
                "actual_status": "api_error",
                "actual_answer": str(detail),
                "elapsed_ms": elapsed,
                "failure_reason": f"HTTP {resp.status_code}: {detail}",
            }

        data = resp.json()
        actual_status = data.get("status", "")
        actual_answer = data.get("answer", "")
        evidence = data.get("evidence", [])

        # 1. Status matches
        expected_status = case.get("expected_status", "")
        status_ok = actual_status == expected_status

        # 2. Answer contains expected keywords
        expected_contains = case.get("expected_answer_contains", [])
        answer_upper = actual_answer.upper()
        contains_ok = all(kw.upper() in answer_upper for kw in expected_contains) if expected_contains else True

        # 3. Evidence references expected fields
        expected_fields = case.get("expected_fields", [])
        all_source_fields = [f for ev in evidence for f in ev.get("source_fields", [])]

        def normalize_field(f: str) -> str:
            return f.split(".")[-1].replace("_", "").lower()

        normalized_sources = {normalize_field(f) for f in all_source_fields}
        fields_ok = all(
            normalize_field(f) in normalized_sources or f in all_source_fields
            for f in expected_fields
        ) if expected_fields else True

        passed = status_ok and contains_ok and fields_ok
        failure_reasons = []
        if not status_ok:
            failure_reasons.append(f"Status: expected '{expected_status}', got '{actual_status}'")
        if not contains_ok:
            missing = [kw for kw in expected_contains if kw.upper() not in answer_upper]
            failure_reasons.append(f"Missing keywords: {missing}")
        if not fields_ok:
            missing_f = [f for f in expected_fields if not (normalize_field(f) in normalized_sources or f in all_source_fields)]
            failure_reasons.append(f"Missing evidence fields: {missing_f}")

        return {
            **case,
            "passed": passed,
            "actual_status": actual_status,
            "actual_answer": actual_answer,
            "elapsed_ms": elapsed,
            "failure_reason": "; ".join(failure_reasons) if failure_reasons else "",
            "evidence_count": len(evidence),
        }
    except Exception as e:
        elapsed = round((time.time() - start) * 1000)
        return {
            **case,
            "passed": False,
            "actual_status": "exception",
            "actual_answer": "",
            "elapsed_ms": elapsed,
            "failure_reason": str(e),
        }


def evaluate_security_case(case: dict, base_url: str) -> dict:
    start = time.time()
    uid = case.get("user_id", "U0000000001")
    attack = case.get("attack", "")

    if case.get("category") == "oversized_input":
        question = ("data " * 250) + attack
    else:
        question = attack

    try:
        resp = requests.post(
            f"{base_url}/chat",
            json={"question": question, "user_id": uid},
            timeout=90,
        )
        elapsed = round((time.time() - start) * 1000)
        if resp.status_code in (400, 422):
            return {
                **case,
                "passed": True,
                "actual_outcome": "blocked_by_guardrail",
                "elapsed_ms": elapsed,
            }
        if resp.status_code == 429:
            return {
                **case,
                "passed": True,
                "actual_outcome": "rate_limited",
                "elapsed_ms": elapsed,
            }
        if resp.status_code != 200:
            return {
                **case,
                "passed": False,
                "actual_outcome": f"unexpected HTTP {resp.status_code}",
                "elapsed_ms": elapsed,
            }

        data = resp.json()
        actual_status = data.get("status", "")
        expected_status = case.get("expected_status", "refused")

        if "or" in expected_status:
            options = [s.strip() for s in expected_status.split("or")]
            passed = actual_status in options
        else:
            passed = actual_status == expected_status

        return {
            **case,
            "passed": passed,
            "actual_outcome": actual_status,
            "actual_answer": data.get("answer", ""),
            "elapsed_ms": elapsed,
        }
    except Exception as e:
        elapsed = round((time.time() - start) * 1000)
        return {
            **case,
            "passed": False,
            "actual_outcome": "exception",
            "elapsed_ms": elapsed,
            "failure_reason": str(e),
        }


def main():
    parser = argparse.ArgumentParser(description="Run RAG agent evaluation suites")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of FastAPI service")
    parser.add_argument("--suite", choices=["all", "golden", "security"], default="all")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay in seconds between calls")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")

    # Check health
    try:
        health_resp = requests.get(f"{base_url}/health", timeout=15)
        if health_resp.status_code != 200:
            print(f"[!] Warning: Health endpoint returned HTTP {health_resp.status_code}")
        else:
            print(f"[+] Connected to API at {base_url} (Health: OK)")
    except Exception as e:
        print(f"[!] Could not connect to API at {base_url}: {e}")
        print("Please ensure the backend is running (`uvicorn app.main:app --port 8000`)")
        sys.exit(1)

    golden_cases = load_jsonl(EVAL_DIR / "golden_questions.jsonl")
    security_cases = load_jsonl(EVAL_DIR / "security_cases.jsonl")

    golden_results = []
    sec_results = []

    if args.suite in ("all", "golden"):
        print(f"\n--- Running Golden Question Suite ({len(golden_cases)} cases) ---")
        for i, c in enumerate(golden_cases, 1):
            sys.stdout.write(f"[{i}/{len(golden_cases)}] {c['question'][:50]}... ")
            sys.stdout.flush()
            r = evaluate_golden_case(c, base_url)
            golden_results.append(r)
            status_str = "PASS" if r["passed"] else "FAIL"
            print(f"[{status_str}] ({r['elapsed_ms']}ms)")
            if not r["passed"]:
                print(f"    Reason: {r.get('failure_reason')}")
            if args.delay > 0:
                time.sleep(args.delay)

    if args.suite in ("all", "security"):
        print(f"\n--- Running Security Test Suite ({len(security_cases)} cases) ---")
        for i, c in enumerate(security_cases, 1):
            sys.stdout.write(f"[{i}/{len(security_cases)}] [{c.get('id', 'SEC')}] {c.get('category')}... ")
            sys.stdout.flush()
            r = evaluate_security_case(c, base_url)
            sec_results.append(r)
            status_str = "PASS" if r["passed"] else "FAIL"
            print(f"[{status_str}] ({r['elapsed_ms']}ms) -> {r.get('actual_outcome')}")
            if not r["passed"]:
                print(f"    Reason: {r.get('failure_reason', 'Did not match expected status')}")
            if args.delay > 0:
                time.sleep(args.delay)

    # Summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)

    if golden_results:
        g_pass = sum(1 for r in golden_results if r.get("passed"))
        g_pct = (g_pass / len(golden_results)) * 100
        print(f"Golden Questions: {g_pass}/{len(golden_results)} passed ({g_pct:.1f}%)")

    if sec_results:
        s_pass = sum(1 for r in sec_results if r.get("passed"))
        s_pct = (s_pass / len(sec_results)) * 100
        print(f"Security Cases:   {s_pass}/{len(sec_results)} passed ({s_pct:.1f}%)")

    all_results = golden_results + sec_results
    if all_results:
        avg_lat = sum(r.get("elapsed_ms", 0) for r in all_results) / len(all_results)
        print(f"Average Latency:  {avg_lat:.0f}ms")
    print("=" * 60)


if __name__ == "__main__":
    main()
