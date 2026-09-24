class GatewayError(Exception):
    status_code: int = 500
    code: str = "internal_error"
    error_type: str = "api_error"
    default_message: str = "Gateway error"

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)

    def to_response(self) -> dict:
        return {
            "error": {
                "message": self.message,
                "type": self.error_type,
                "code": self.code,
                "param": None,
            }
        }


class UnknownModelError(GatewayError):
    status_code = 404
    code = "model_not_found"
    error_type = "invalid_request_error"
    default_message = "The requested model does not exist or is not registered."


class SessionExpiredError(GatewayError):
    status_code = 401
    code = "session_invalid"
    error_type = "authentication_error"
    default_message = "The provider session is invalid or expired."


class WAFChallengeError(GatewayError):
    status_code = 403
    code = "waf_challenge"
    error_type = "permission_error"
    default_message = "The provider returned a WAF challenge for this request."


class RateLimitedError(GatewayError):
    status_code = 429
    code = "rate_limited"
    error_type = "rate_limit_error"
    default_message = "The provider is rate limiting this account."