import os

# Use the test collection, not the production collection.
os.environ["MILVUS_COLLECTION"] = "customer_summaries_test"

from app.agent.orchestrator import run_agent


def main():
    user_id = "U0000000001"

    questions = [
        "What is the customer's subscription plan and status?",
        "How many payment attempts did the customer make, and what is the net revenue?",
        "How many usage events does the customer have?",
    ]

    for question in questions:
        print("\n" + "=" * 70)
        print("Question:", question)

        result = run_agent(
            question=question,
            user_id=user_id,
        )

        print("\nStatus:", result.status)
        print("Answer:", result.answer)
        print("Evidence:", result.evidence)
        print("Limitations:", result.limitations)


if __name__ == "__main__":
    main()