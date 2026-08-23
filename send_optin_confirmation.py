"""
Run this ONCE, right after adding YOUR_PHONE_NUMBER to .env, to send
yourself a real opt-in confirmation text. This makes the "confirmation
message" you describe in Twilio's campaign registration literally true,
rather than just a description with nothing behind it.

Usage: python3 send_optin_confirmation.py
"""
from src.notifier import send_text

CONFIRMATION_MESSAGE = (
    "JHD Football Agent: Welcome! You'll receive personal fantasy "
    "football alerts. Msg frequency varies. Msg & data rates may apply. "
    "Reply HELP for help, STOP to cancel."
)

if __name__ == "__main__":
    send_text(CONFIRMATION_MESSAGE)
    print("Confirmation message sent. Check your phone.")
