from slowapi import Limiter
from slowapi.util import get_remote_address

# We will attach key_func inside main.py to avoid circular imports, but we need the Limiter instance here.
limiter = Limiter(key_func=get_remote_address)
