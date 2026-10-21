from app.agent.tools import get_payment_summary

try:
    get_payment_summary(
        user_id="U0000000002",
        authorized_user_id="U0000000001",
    )
    print("FAIL: Unauthorized access was allowed.")

except PermissionError:
    print("PASS: Unauthorized access was blocked.")