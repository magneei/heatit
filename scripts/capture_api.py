"""
mitmproxy addon to capture and log Heatit WiFi app API traffic.

Usage:
    mitmweb --set console_eventlog_verbosity=info -s scripts/capture_api.py

Then configure your phone to proxy through this Mac's IP on port 8080.
Open the Heatit WiFi app and perform these actions:
    1. Open the app (observe login/auth flow)
    2. View thermostat status
    3. Change target temperature
    4. Change operating mode (heat/cool/eco/off)
    5. View energy/consumption data

Captured flows will be saved to docs/captured_flows.json
"""

import json
import time
from pathlib import Path

from mitmproxy import http, ctx

OUTPUT_FILE = Path(__file__).parent.parent / "docs" / "captured_flows.json"
captured = []


def response(flow: http.HTTPFlow) -> None:
    """Called when a response is received. Log all flows for analysis."""
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "request": {
            "method": flow.request.method,
            "url": flow.request.pretty_url,
            "host": flow.request.pretty_host,
            "path": flow.request.path,
            "headers": dict(flow.request.headers),
            "body": flow.request.get_text(),
        },
        "response": {
            "status_code": flow.response.status_code,
            "headers": dict(flow.response.headers),
            "body": _try_parse_json(flow.response.get_text()),
        },
    }

    captured.append(entry)
    _save()

    # Highlight interesting traffic in the mitmproxy log
    host = flow.request.pretty_host.lower()
    keywords = ["heatit", "thermofloor", "thermo", "heat"]
    if any(kw in host for kw in keywords):
        ctx.log.info(
            f"*** HEATIT API: {flow.request.method} {flow.request.path} "
            f"-> {flow.response.status_code}"
        )


def _try_parse_json(text: str):
    """Try to parse as JSON, return raw text if it fails."""
    if not text:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return text


def _save():
    """Save captured flows to disk."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(captured, indent=2, default=str))


def done():
    """Called when mitmproxy shuts down."""
    _save()
    ctx.log.info(f"Saved {len(captured)} captured flows to {OUTPUT_FILE}")
