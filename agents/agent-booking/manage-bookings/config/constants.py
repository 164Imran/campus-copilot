from os import getenv
from dotenv import load_dotenv

AUTH_BASE_URL = "https://auth.anny.eu"
ANNY_BASE_URL = "https://anny.eu"
BOOKING_API_BASE = "https://b.anny.eu/api/v1"
CHECKOUT_FORM_API = "https://b.anny.eu/api/ui/checkout-form"

DEFAULT_HEADERS = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0',
    'accept-encoding': 'plain'
}

load_dotenv('.env', override=True)

USERNAME = getenv("USERNAME")
PASSWORD = getenv("PASSWORD")
TIMEZONE = getenv("TIMEZONE") or "Europe/Berlin"
RESOURCE_URL_PATH = getenv("RESOURCE_URL_PATH")
SERVICE_ID = getenv("SERVICE_ID")
RESOURCE_URL = f"{BOOKING_API_BASE}{RESOURCE_URL_PATH}" if RESOURCE_URL_PATH else None

BOOKING_TIMES_CSV = getenv("BOOKING_TIMES") or ""
BOOKING_TIMES = [{"start": b.split("-")[0].strip(), "end": b.split("-")[1].strip()} for b in BOOKING_TIMES_CSV.split(",") if "-" in b]
