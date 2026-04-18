import os
from auth.session import AnnySession
from booking_client import BookingClient
from utils.helpers import get_future_datetime
from config.constants import USERNAME, PASSWORD, BOOKING_TIMES

def main():
    target_days_ahead = int(os.getenv("TARGET_DAYS_AHEAD", "0"))
    session = AnnySession(USERNAME, PASSWORD, provider_name="tum")
    cookies = session.login()
    if not cookies: return False
    booking = BookingClient(cookies, customer_account_id=session.customer_account_id)
    
    for time_ in BOOKING_TIMES:
        start = get_future_datetime(days_ahead=target_days_ahead, time_string=time_['start'])
        end = get_future_datetime(days_ahead=target_days_ahead, time_string=time_['end'])
        r_ids = booking.find_available_resources(start, end)
        if r_ids:
            if booking.reserve(r_ids[0], start, end):
                print("✅ Success")
                return True
    print("❌ Failed")

if __name__ == "__main__":
    main()
