from auth.providers.base import SSOProvider
from utils.helpers import extract_html_value

class TUMProvider(SSOProvider):
    def __init__(self, username, password):
        super().__init__(username, password)
        self.name = "TUM"

    def authenticate(self, session, url):
        # Initial SSO Redirect
        r = session.get("https://auth.anny.eu/login/sso/tum")
        # Extract SAML Request
        action = extract_html_value(r.text, r'action="(.*?)"')
        saml_request = extract_html_value(r.text, r'name="SAMLRequest" value="(.*?)"')
        relay_state = extract_html_value(r.text, r'name="RelayState" value="(.*?)"')
        
        # Shibboleth Login
        r = session.post(action, data={'SAMLRequest': saml_request, 'RelayState': relay_state})
        exec_val = extract_html_value(r.text, r'name="execution" value="(.*?)"')
        
        r = session.post(r.url, data={'j_username': self.username, 'j_password': self.password, '_eventId_proceed': '', 'execution': exec_val})
        if "Authentication failed" in r.text:
            raise ValueError("Invalid TUM credentials")
            
        # SAML Response
        action = extract_html_value(r.text, r'action="(.*?)"')
        saml_response = extract_html_value(r.text, r'name="SAMLResponse" value="(.*?)"')
        relay_state = extract_html_value(r.text, r'name="RelayState" value="(.*?)"')
        
        session.post(action, data={'SAMLResponse': saml_response, 'RelayState': relay_state})
