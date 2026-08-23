"""
Sends SMS alerts via Twilio. Costs roughly $0.01 per text.
"""
from __future__ import annotations
import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()


def send_text(message: str) -> None:
    client = Client(
        os.environ["TWILIO_ACCOUNT_SID"],
        os.environ["TWILIO_AUTH_TOKEN"],
    )
    client.messages.create(
        body=message,
        from_=os.environ["TWILIO_FROM_NUMBER"],
        to=os.environ["YOUR_PHONE_NUMBER"],
    )
