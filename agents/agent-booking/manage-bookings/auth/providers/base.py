class SSOProvider:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.name = "SSO"
    def authenticate(self, session, url):
        pass
