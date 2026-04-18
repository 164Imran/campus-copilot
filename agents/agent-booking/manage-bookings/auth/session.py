import requests
import urllib.parse
from config.constants import AUTH_BASE_URL, ANNY_BASE_URL, DEFAULT_HEADERS
from utils.helpers import extract_html_value
from auth.providers import get_provider, SSOProvider

class AnnySession:
    def __init__(self, username: str, password: str, provider_name: str):
        self.session = requests.Session()
        self.username = username
        self.password = password
        provider_class = get_provider(provider_name)
        self.provider: SSOProvider = provider_class(username, password)

    def login(self):
        try:
            self.session.headers.update({**DEFAULT_HEADERS, 'accept': 'text/html, application/xhtml+xml', 'referer': AUTH_BASE_URL + '/', 'origin': AUTH_BASE_URL})
            r1 = self.session.get(f"{AUTH_BASE_URL}/login/sso")
            self.session.headers['X-XSRF-TOKEN'] = urllib.parse.unquote(r1.cookies['XSRF-TOKEN'])
            page_data = extract_html_value(r1.text, r'data-page="(.*?)"')
            self.customer_account_id = 1 # Simplified for TUM
            self.provider.authenticate(self.session, "")
            return self.session.cookies
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return None
