"""Twitch Helix clips lookup.

When the streamer is on Twitch this beats any heuristic: viewers already
clipped the good moments and the view counts rank them. Needs an app token --
register at https://dev.twitch.tv/console/apps and export:

    TWITCH_CLIENT_ID=...
    TWITCH_CLIENT_SECRET=...

Falls back silently (returns None) when credentials are absent so the CLI can
drop through to loudness detection.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

_HELIX = "https://api.twitch.tv/helix"
_OAUTH = "https://id.twitch.tv/oauth2/token"


@dataclass(frozen=True)
class TwitchClip:
    id: str
    title: str
    url: str
    views: int
    duration: float
    creator: str
    created_at: str


def _get_json(url: str, headers: dict[str, str]) -> dict:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def app_token() -> tuple[str, str] | None:
    """Client-credentials token, or None if creds are not configured."""
    client_id = os.environ.get("TWITCH_CLIENT_ID")
    secret = os.environ.get("TWITCH_CLIENT_SECRET")
    if not client_id or not secret:
        return None
    body = urllib.parse.urlencode(
        {"client_id": client_id, "client_secret": secret, "grant_type": "client_credentials"}
    ).encode()
    with urllib.request.urlopen(_OAUTH, data=body, timeout=30) as resp:
        payload = json.load(resp)
    return client_id, payload["access_token"]


def _headers(client_id: str, token: str) -> dict[str, str]:
    return {"Client-Id": client_id, "Authorization": f"Bearer {token}"}


def broadcaster_id(login: str, client_id: str, token: str) -> str | None:
    query = urllib.parse.urlencode({"login": login})
    data = _get_json(f"{_HELIX}/users?{query}", _headers(client_id, token))
    entries = data.get("data") or []
    return entries[0]["id"] if entries else None


def top_clips(login: str, *, days: int = 30, limit: int = 20) -> list[TwitchClip] | None:
    """Most-viewed clips of a channel in the last `days`. None if no credentials."""
    creds = app_token()
    if creds is None:
        return None
    client_id, token = creds

    bid = broadcaster_id(login, client_id, token)
    if bid is None:
        raise RuntimeError(f"no Twitch channel called {login!r}")

    started = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
    collected: list[TwitchClip] = []
    cursor: str | None = None

    while len(collected) < limit:
        params = {
            "broadcaster_id": bid,
            "started_at": started,
            "first": str(min(100, limit - len(collected))),
        }
        if cursor:
            params["after"] = cursor
        data = _get_json(
            f"{_HELIX}/clips?{urllib.parse.urlencode(params)}", _headers(client_id, token)
        )
        batch = data.get("data") or []
        if not batch:
            break
        for c in batch:
            collected.append(
                TwitchClip(
                    id=c["id"],
                    title=c.get("title") or c["id"],
                    url=c["url"],
                    views=int(c.get("view_count") or 0),
                    duration=float(c.get("duration") or 0.0),
                    creator=c.get("creator_name") or "",
                    created_at=c.get("created_at") or "",
                )
            )
        cursor = (data.get("pagination") or {}).get("cursor")
        if not cursor:
            break

    collected.sort(key=lambda c: c.views, reverse=True)
    return collected[:limit]
