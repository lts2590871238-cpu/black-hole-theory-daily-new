"""Shared HTTP policy for official APIs."""

from __future__ import annotations

from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def build_session(user_agent: str, attempts: int, backoff: float) -> Session:
    retry = Retry(
        total=attempts,
        connect=attempts,
        read=attempts,
        status=attempts,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        backoff_factor=backoff,
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    session = Session()
    session.headers.update(
        {"User-Agent": user_agent, "Accept": "application/json, application/atom+xml"}
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session
