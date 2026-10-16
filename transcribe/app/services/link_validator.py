"""
Meeting link validation and normalization.
Supports Google Meet, Zoom, and Microsoft Teams.
"""
from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass
from app.models.orm import PlatformEnum


class InvalidMeetingLink(Exception):
    """Raised when a meeting link is invalid or unsupported."""
    pass


@dataclass
class NormalizedLink:
    platform: PlatformEnum
    url: str


_GMEET_PATH_PATTERN = re.compile(r"^/[a-z]{3}-[a-z]{4}-[a-z]{3}$")
_ZOOM_PATH_PATTERN = re.compile(r"^/j/\d+$")


def validate_and_normalize(link: str) -> NormalizedLink:
    """
    Validates and normalizes meeting URLs.
    
    Allowed hosts:
      - meet.google.com (path matching /xxx-yyyy-zzz)
      - *.zoom.us (path starting /j/<digits>)
      - teams.microsoft.com, teams.live.com (path starting /l/meetup-join or /meet/)
      
    Normalization:
      - Strips whitespace
      - Enforces https scheme
      - Drops tracking parameters (utm_*, authuser, pli, hs, etc.) while keeping Zoom 'pwd' and Teams params
    """
    if not link or not isinstance(link, str):
        raise InvalidMeetingLink("Meeting link must be a non-empty string.")

    raw = link.strip()
    if len(raw) > 2048:
        raise InvalidMeetingLink("Meeting link exceeds maximum length of 2048 characters.")

    # Reject whitespace inside link
    if any(c.isspace() for c in raw):
        raise InvalidMeetingLink("Meeting link contains invalid whitespace characters.")

    # Force scheme if missing
    if not raw.startswith("http://") and not raw.startswith("https://"):
        raw = "https://" + raw

    try:
        parsed = urllib.parse.urlsplit(raw)
    except Exception as e:
        raise InvalidMeetingLink(f"Malformed URL: {e}")

    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise InvalidMeetingLink(f"Unsupported URL scheme: {scheme}")

    host = (parsed.hostname or "").lower()
    path = parsed.path
    query_params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)

    # 1. Google Meet
    if host == "meet.google.com":
        clean_path = path.lower()
        if not _GMEET_PATH_PATTERN.match(clean_path):
            raise InvalidMeetingLink(f"Invalid Google Meet path format: '{path}'. Expected format '/xxx-yyyy-zzz'.")
        # Google Meet does not need query parameters
        normalized_url = f"https://meet.google.com{clean_path}"
        return NormalizedLink(platform=PlatformEnum.GOOGLE_MEET, url=normalized_url)

    # 2. Zoom (*.zoom.us or zoom.us)
    elif host == "zoom.us" or host.endswith(".zoom.us"):
        clean_path = path
        if not _ZOOM_PATH_PATTERN.match(clean_path):
            raise InvalidMeetingLink(f"Invalid Zoom path: '{path}'. Expected '/j/<digits>'.")
        # Keep 'pwd' parameter if present, discard tracking parameters
        kept_params = {}
        if "pwd" in query_params and query_params["pwd"]:
            kept_params["pwd"] = query_params["pwd"][0]
        qs = urllib.parse.urlencode(kept_params)
        normalized_url = f"https://{host}{clean_path}" + (f"?{qs}" if qs else "")
        return NormalizedLink(platform=PlatformEnum.ZOOM, url=normalized_url)

    # 3. Microsoft Teams
    elif host in ("teams.microsoft.com", "teams.live.com"):
        if not (path.startswith("/l/meetup-join") or path.startswith("/meet/")):
            raise InvalidMeetingLink(f"Invalid Teams meeting path: '{path}'.")
        # Discard utm tracking params but keep Teams context params
        kept_params = {}
        for k, v in query_params.items():
            k_lower = k.lower()
            if not (k_lower.startswith("utm_") or k_lower in ("authuser", "pli", "hs")):
                kept_params[k] = v[0] if len(v) == 1 else v
        qs = urllib.parse.urlencode(kept_params, doseq=True)
        normalized_url = f"https://{host}{path}" + (f"?{qs}" if qs else "")
        return NormalizedLink(platform=PlatformEnum.TEAMS, url=normalized_url)

    else:
        raise InvalidMeetingLink(f"Unsupported meeting host: '{host}'. Allowed: Google Meet, Zoom, MS Teams.")
