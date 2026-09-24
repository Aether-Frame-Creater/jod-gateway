import hashlib
import json

from jod_gateway.core.session import Session
from jod_gateway.providers.chatgpt.pow import build_pow_config


# ALGORITHM UNSTABLE — may need adjustment. The prepare request's `p` field is
# a hash of the client config shape (no nonce). If the live server rejects it,
# capture the raw /prepare response and reverse the expected `p` format.
def build_requirements_token(session: Session) -> str:
    config = build_pow_config(session)
    payload = json.dumps(config, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()