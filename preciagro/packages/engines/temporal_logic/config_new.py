"""Configuration management for Temporal Logic Engine."""

import os

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
JWT_PUBKEY = os.getenv("SERVICE_JWT_PUBLIC_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM")
MAX_NOTIFICATIONS_PER_DAY = int(os.getenv("MAX_NOTIFS_PER_DAY", "5"))
DIGEST_HOUR_LOCAL = int(os.getenv("DIGEST_HOUR_LOCAL", "19"))
