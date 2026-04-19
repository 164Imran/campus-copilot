import datetime
import os
import pytz

from auth.session import AnnySession
from booking_client import BookingClient, CheckoutException
from utils.helpers import get_future_datetime
from config.constants import USERNAME, PASSWORD, RESOURCE_URL_PATH, SERVICE_ID, TIMEZONE, BOOKING_TIMES

def main():
    if not USERNAME or not PASSWORD:
        print("❌ Missing USERNAME or PASSWORD in .env")
        return False

    if not BOOKING_TIMES:
        print("❌ Missing BOOKING_TIMES in .env")
        return False

    target_days_ahead = int(os.getenv("TARGET_DAYS_AHEAD", "0"))

    session = AnnySession(USERNAME, PASSWORD, provider_name="tum")
    cookies = session.login()

    if not cookies:
        print("❌ Login failed")
        return False

    booking = BookingClient(cookies, customer_account_id=session.customer_account_id)

    # Force auto-discovery bypass if env vars are present
    if RESOURCE_URL_PATH and SERVICE_ID:
        booking.resource_url = f"https://b.anny.eu/api/v1{RESOURCE_URL_PATH}"
        booking.service_id = SERVICE_ID
    else:
        print("❌ RESOURCE_URL_PATH and SERVICE_ID must be set in .env")
        return False

    print(f"🚀 Attempting immediate booking for {target_days_ahead} days ahead...")

    for time_ in BOOKING_TIMES:
        try:
            start = get_future_datetime(days_ahead=target_days_ahead, time_string=time_['start'])
            end = get_future_datetime(days_ahead=target_days_ahead, time_string=time_['end'])

            r_ids_available = booking.find_available_resources(start, end)

            if r_ids_available is None or not r_ids_available:
                print(f"⚠️ No resources available for {time_['start']}-{time_['end']}")
                continue

            for i, r_id in enumerate(r_ids_available):
                try:
                    success = booking.reserve(r_id, start, end)
                except CheckoutException:
                    print(f"⚠️ Checkout failed for {time_['start']}-{time_['end']}")
                    break

                if success:
                    return True
            else:
                print(f"⚠️ Failed to book any slots for {time_['start']}-{time_['end']}")
        except Exception as e:
            print(f"❌ Error booking slot {time_['start']}-{time_['end']}: {type(e).__name__}: {e}")
            break

if __name__ == "__main__":
    main()
