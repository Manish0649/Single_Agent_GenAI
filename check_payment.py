import os

os.environ["MILVUS_COLLECTION"] = "customer_summaries_test"

from app.agent.tools import get_payment_summary

user_id = "U0000000001"

result = get_payment_summary(
    user_id=user_id,
    authorized_user_id=user_id
)

print("Payment summary:")
for key, value in result.items():
    print(f"{key}: {value}")

print("\nFinancial amounts in INR:")
for key in [
    "total_invoiced_paise",
    "total_settled_paise",
    "net_revenue_paise",
    "refund_amount_paise",
]:
    value = result.get(key)

    if value is not None:
        print(f"{key}: ₹{value / 100:.2f}")