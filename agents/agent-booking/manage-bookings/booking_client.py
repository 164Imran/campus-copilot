import requests
from requests.exceptions import JSONDecodeError
from config.constants import RESOURCE_URL, BOOKING_API_BASE, CHECKOUT_FORM_API, ANNY_BASE_URL, SERVICE_ID

class CheckoutException(Exception):
    pass

class BookingClient:
    def __init__(self, cookies, customer_account_id=None):
        self.session = requests.Session()
        self.session.cookies = cookies
        self.token = cookies.get('anny_shop_jwt')
        self.resource_url = RESOURCE_URL
        self.service_id = SERVICE_ID
        self.customer_account_id = customer_account_id

        self.session.headers.update({
            'authorization': f'Bearer {self.token}',
            'accept': 'application/vnd.api+json',
            'content-type': 'application/vnd.api+json',
            'origin': ANNY_BASE_URL,
            'referer': ANNY_BASE_URL + '/',
            'user-agent': 'Mozilla/5.0'
        })

    def find_available_resources(self, start, end):
        response = self.session.get(self.resource_url, params={
            'page[number]': 1, 'page[size]': 250,
            'filter[available_from]': start, 'filter[available_to]': end,
            'filter[availability_exact_match]': 1, 'filter[availability_service_id]': int(self.service_id),
            'sort': 'name'
        })
        if not response.ok: return None
        try: return [r['id'] for r in response.json().get('data', [])]
        except: return None

    def reserve(self, resource_id, start, end):
        booking = self.session.post(f"{BOOKING_API_BASE}/order/bookings", params={'stateless': '1'}, json={
            "resource_id": [resource_id], "service_id": {self.service_id: 1},
            "start_date": start, "end_date": end, "strategy": "multi-resource"
        })
        if not booking.ok: return False
        data = booking.json().get("data", {})
        oid, oat = data.get("id"), data.get("attributes", {}).get("access_token")
        checkout = self.session.get(f"{CHECKOUT_FORM_API}?oid={oid}&oat={oat}&stateless=1")
        customer = checkout.json().get("default", {}).get("customer", {})
        final = self.session.post(f"{BOOKING_API_BASE}/order", params={"stateless": "1", "oid": oid, "oat": oat}, json={
            "customer": {"given_name": customer.get("given_name"), "family_name": customer.get("family_name"), "email": customer.get("email")},
            "accept_terms": True, "success_url": f"{ANNY_BASE_URL}/checkout/success", "meta": {"timezone": "Europe/Berlin"}
        })
        return final.ok

    def get_active_bookings(self):
        response = self.session.get(f"{BOOKING_API_BASE}/bookings")
        if not response.ok: return []
        return response.json().get('data', [])

    def cancel_booking(self, booking_id):
        response = self.session.get(f"{BOOKING_API_BASE}/bookings/{booking_id}/cancel")
        return response.ok
