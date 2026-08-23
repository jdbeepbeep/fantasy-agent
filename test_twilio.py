"""
One-off test to confirm Twilio is wired up correctly. Sends a single
test text to your phone. Run with: python3 test_twilio.py
"""
from src.notifier import send_text

if __name__ == "__main__":
    send_text("Fantasy agent test text -- if you got this, Twilio is working!")
    print("Text sent. Check your phone.")
