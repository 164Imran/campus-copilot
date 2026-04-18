import os
from auth.session import AnnySession
from booking_client import BookingClient

def main():
    target_date = os.getenv("CANCEL_DATE")
    session = AnnySession(os.getenv("USERNAME"), os.getenv("PASSWORD"), provider_name="tum")
    cookies = session.login()
    if not cookies: return False
    booking = BookingClient(cookies, customer_account_id=session.customer_account_id)
    active = booking.get_active_bookings()
    for b in active:
        start_date = b.get('attributes', {}).get('start_date')
        if start_date and start_date.startswith(target_date):
            if booking.cancel_booking(b.get('id')):
                print(f"✅ Canceled {b.get('id')}")
                return True
    print("❌ Not found")

if __name__ == "__main__":
    main()
