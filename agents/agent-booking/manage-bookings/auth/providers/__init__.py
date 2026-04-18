from auth.providers.base import SSOProvider
from auth.providers.tum import TUMProvider

PROVIDERS = {"tum": TUMProvider}

def get_provider(name: str):
    return PROVIDERS.get(name.lower(), TUMProvider)
