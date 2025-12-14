# app/core/guardrails.py
import re
import time
from collections import defaultdict
from typing import Literal

# 1. PII / Sensitive Info — pure regex, instant
PII_PATTERNS = [
    r'\b\d{3}-\d{2}-\d{4}\b',                    # SSN
    r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', # Credit card
    r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}', # Email
    r'AKIA[0-9A-Z]{16}',                         # AWS Access Key
    r'ghp_[0-9a-zA-Z]{36}',                      # GitHub PAT
]

PII_REGEX = re.compile("|".join(PII_PATTERNS), re.IGNORECASE)

def contains_pii(text: str) -> bool:
    return bool(PII_REGEX.search(text))

# 2. Rate limiting — per user/session, in-memory or Redis
class RateLimiter:
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = defaultdict(list[float])

    def allow(self, user_id: str) -> tuple[bool, int]:  # returns (allowed, seconds_until_reset)
        now = time.time()
        self.requests[user_id] = [t for t in self.requests[user_id] if now - t < self.window]
        
        if len(self.requests[user_id]) >= self.max_requests:
            reset_in = int(self.window - (now - self.requests[user_id][0]))
            return False, max(1, reset_in)
        
        self.requests[user_id].append(now)
        return True, 0

# Global limiter (or inject per instance)
rate_limiter = RateLimiter(max_requests=40, window_seconds=60)