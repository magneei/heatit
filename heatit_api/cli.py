#!/usr/bin/env python3
"""CLI tool for testing the Heatit WiFi thermostat API."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

from .client import HeatitClient
from .models import OperatingMode


async def cmd_login(client: HeatitClient, args: argparse.Namespace) -> None:
    email = await client.async_login()
    print(f"Logged in as: {email}")


async def cmd_devices(client: HeatitClient, args: argparse.Namespace) -> None:
    devices = await client.async_get_devices()
    if not devices:
        print("No devices found.")
        return
    for d in devices:
        online = "online" if d.online else "OFFLINE"
        print(f"  {d.device_id}  {d.display_name or d.device_type:20s}  "
              f"zone={d.zone_name:15s}  {online}  "
              f"mac={d.mac_addr}  fw={d.sw_ver}")


async def cmd_status(client: HeatitClient, args: argparse.Namespace) -> None:
    device_id = await _resolve_device_id(client, args.device_id)
    device = await client.async_get_device(device_id)

    c = device.config
    s = device.sensors
    i = device.info

    print(f"  Device:      {c.display_name} ({i.device_type})")
    print(f"  Zone:        {i.zone_name}")
    print(f"  Device ID:   {i.device_id}")
    print(f"  MAC:         {i.mac_addr}")
    print(f"  Serial:      {i.serial_num}")
    print(f"  Firmware:    {i.sw_ver} (hw: {i.hw_ver})")
    print(f"  Online:      {'Yes' if c.online else 'NO'}")
    print()
    print(f"  Mode:        {c.op_mode.label} (opMode={c.op_mode.value})")
    print(f"  Set point:   {c.set_point:.1f}°C")
    print(f"  Away temp:   {c.away_set_point:.1f}°C")
    print()
    if s:
        heating = "HEATING" if s.relay_state else "idle"
        print(f"  State:       {heating}")
        print(f"  Current:     {s.current_temp:.1f}°C")
        print(f"  Floor:       {s.floor_temp:.1f}°C")
        print(f"  Room:        {s.room_temp:.1f}°C")
        print(f"  External:    {s.external_temp:.1f}°C")
        print(f"  WiFi RSSI:   {s.rssi} dBm")


async def cmd_set_temp(client: HeatitClient, args: argparse.Namespace) -> None:
    device_id = await _resolve_device_id(client, args.device_id)
    ok = await client.async_set_temperature(device_id, args.temperature)
    if ok:
        print(f"Temperature set to {args.temperature:.1f}°C")
    else:
        print("Failed to set temperature", file=sys.stderr)
        sys.exit(1)


async def cmd_set_mode(client: HeatitClient, args: argparse.Namespace) -> None:
    device_id = await _resolve_device_id(client, args.device_id)
    mode_map = {
        "home": OperatingMode.HOME,
        "away": OperatingMode.AWAY,
        "timeplan": OperatingMode.TIMEPLAN,
        "antifreeze": OperatingMode.ANTIFREEZE,
        "energy": OperatingMode.ENERGY_MANAGEMENT,
    }
    mode = mode_map[args.mode.lower()]
    ok = await client.async_set_mode(device_id, mode)
    if ok:
        print(f"Mode set to {mode.name}")
    else:
        print("Failed to set mode", file=sys.stderr)
        sys.exit(1)


async def _resolve_device_id(
    client: HeatitClient, device_id: str | None
) -> str:
    """If no device_id given, auto-select the first (or only) device."""
    if device_id:
        return device_id
    devices = await client.async_get_devices()
    if not devices:
        print("No devices found.", file=sys.stderr)
        sys.exit(1)
    if len(devices) == 1:
        return devices[0].device_id
    print("Multiple devices found. Please specify --device-id:")
    for d in devices:
        print(f"  {d.device_id}  ({d.display_name or d.device_type})")
    sys.exit(1)


async def async_main() -> None:
    parser = argparse.ArgumentParser(
        prog="heatit",
        description="CLI for Heatit WiFi thermostats",
    )
    parser.add_argument("-u", "--username", help="Heatit account email")
    parser.add_argument("-p", "--password", help="Heatit account password")
    parser.add_argument(
        "-d", "--device-id", help="Device UUID (optional if only one device)"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("login", help="Test authentication")
    sub.add_parser("devices", help="List all devices")
    sub.add_parser("status", help="Show device status")

    p_temp = sub.add_parser("set-temp", help="Set target temperature")
    p_temp.add_argument("temperature", type=float, help="Temperature in °C")

    p_mode = sub.add_parser("set-mode", help="Set operating mode")
    p_mode.add_argument("mode", choices=["home", "away", "timeplan", "antifreeze", "energy"])

    args = parser.parse_args()

    username = args.username or input("Email: ")
    password = args.password or getpass.getpass("Password: ")

    commands = {
        "login": cmd_login,
        "devices": cmd_devices,
        "status": cmd_status,
        "set-temp": cmd_set_temp,
        "set-mode": cmd_set_mode,
    }

    async with HeatitClient(username, password) as client:
        await commands[args.command](client, args)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
