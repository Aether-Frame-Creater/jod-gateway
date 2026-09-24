from jod_gateway.providers.chatgpt.config import BASE_URL, USER_AGENT


def browser_headers(extra: dict | None = None) -> dict:
    headers = {
        "user-agent": USER_AGENT,
        "accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
            "image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
        ),
        "accept-language": "en-US,en;q=0.9",
        "sec-ch-ua": '"Chromium";v="136", "Not.A/Brand";v="99", "Google Chrome";v="136"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "origin": BASE_URL,
        "referer": BASE_URL + "/",
    }
    if extra:
        headers.update(extra)
    return headers