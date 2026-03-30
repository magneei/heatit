#!/usr/bin/env python3
"""
Analyze captured API flows from mitmproxy and extract Heatit-related traffic.

Usage:
    python scripts/analyze_capture.py [docs/captured_flows.json]
"""

import json
import sys
from collections import defaultdict
from pathlib import Path


def analyze(capture_file: str = "docs/captured_flows.json"):
    data = json.loads(Path(capture_file).read_text())
    print(f"Total captured flows: {len(data)}\n")

    # Group by host
    by_host = defaultdict(list)
    for entry in data:
        host = entry["request"]["host"]
        by_host[host].append(entry)

    print("=" * 70)
    print("HOSTS CONTACTED")
    print("=" * 70)
    for host, flows in sorted(by_host.items(), key=lambda x: -len(x[1])):
        print(f"  {host:50s}  ({len(flows)} requests)")

    # Show all unique endpoint patterns
    print(f"\n{'=' * 70}")
    print("UNIQUE ENDPOINTS")
    print("=" * 70)
    seen = set()
    for entry in data:
        key = (entry["request"]["method"], entry["request"]["host"], entry["request"]["path"].split("?")[0])
        if key not in seen:
            seen.add(key)
            req = entry["request"]
            resp = entry["response"]
            print(f"\n  {req['method']:6s} {req['host']}{key[2]}")
            print(f"         Status: {resp['status_code']}")

            # Show auth headers
            for h in ["Authorization", "authorization", "X-Api-Key", "x-api-key",
                       "Cookie", "cookie", "Token", "token"]:
                if h in req["headers"]:
                    val = req["headers"][h]
                    # Truncate long values
                    if len(val) > 80:
                        val = val[:77] + "..."
                    print(f"         {h}: {val}")

            # Show request body summary
            body = req["body"]
            if body:
                if isinstance(body, str) and len(body) > 200:
                    body = body[:197] + "..."
                print(f"         Body: {body}")

            # Show response body summary
            resp_body = resp["body"]
            if resp_body:
                if isinstance(resp_body, dict):
                    keys = list(resp_body.keys())
                    print(f"         Response keys: {keys}")
                elif isinstance(resp_body, str) and len(resp_body) > 200:
                    resp_body = resp_body[:197] + "..."
                    print(f"         Response: {resp_body}")

    # Highlight likely Heatit traffic
    heatit_keywords = ["heatit", "thermofloor", "thermo", "heat"]
    heatit_flows = [
        e for e in data
        if any(kw in e["request"]["host"].lower() for kw in heatit_keywords)
        or any(kw in e["request"]["url"].lower() for kw in heatit_keywords)
    ]

    if heatit_flows:
        print(f"\n{'=' * 70}")
        print(f"HEATIT-SPECIFIC TRAFFIC ({len(heatit_flows)} flows)")
        print("=" * 70)
        for entry in heatit_flows:
            req = entry["request"]
            resp = entry["response"]
            print(f"\n  [{entry['timestamp']}]")
            print(f"  {req['method']} {req['url']}")
            print(f"  Status: {resp['status_code']}")
            print(f"  Request headers: {json.dumps(req['headers'], indent=4)}")
            if req["body"]:
                print(f"  Request body: {json.dumps(req['body'], indent=4) if isinstance(req['body'], (dict, list)) else req['body']}")
            if resp["body"]:
                print(f"  Response body: {json.dumps(resp['body'], indent=4) if isinstance(resp['body'], (dict, list)) else resp['body'][:500]}")
    else:
        print(f"\n{'=' * 70}")
        print("NO HEATIT-SPECIFIC TRAFFIC FOUND")
        print("=" * 70)
        print("The app might use a generic cloud provider (Azure IoT, AWS, Firebase).")
        print("Look at the hosts above for likely candidates.")
        print("Common patterns: *.azure-devices.net, *.amazonaws.com, *.firebaseio.com")


if __name__ == "__main__":
    capture_file = sys.argv[1] if len(sys.argv) > 1 else "docs/captured_flows.json"
    analyze(capture_file)
