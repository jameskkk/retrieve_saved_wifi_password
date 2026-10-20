import argparse
import json
import sys
from typing import Iterable, Optional

from .backends import get_backend
from .errors import WifiPasswordError
from .models import SavedNetwork


def _record(network: SavedNetwork, reveal: bool) -> dict:
    record = {"ssid": network.ssid}
    if network.profile_id and network.profile_id != network.ssid:
        record["profile_id"] = network.profile_id
    if network.interface:
        record["interface"] = network.interface
    if reveal:
        record["password"] = network.password
    if network.error:
        record["error"] = network.error
    return record


def _print_table(networks: Iterable[SavedNetwork], reveal: bool) -> None:
    networks = list(networks)
    if not networks:
        print("No saved Wi-Fi networks found.")
        return
    if not reveal:
        for network in networks:
            print(network.ssid)
        return

    width = max(len(network.ssid) for network in networks)
    for network in networks:
        value = network.password if network.password is not None else f"<unavailable: {network.error}>"
        print(f"{network.ssid:<{width}}  {value}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wifi-passwords",
        description="Retrieve Wi-Fi credentials saved on this computer.",
    )
    parser.add_argument(
        "--platform",
        choices=["macos", "ubuntu", "windows"],
        help=argparse.SUPPRESS,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="list saved Wi-Fi networks")
    list_parser.add_argument(
        "--show-passwords",
        action="store_true",
        help="include plaintext passwords in output",
    )
    list_parser.add_argument("--json", action="store_true", help="emit JSON")

    get_parser = subparsers.add_parser("get", help="print the password for one network")
    get_parser.add_argument("ssid", help="saved network name (SSID)")
    get_parser.add_argument("--json", action="store_true", help="emit JSON")
    return parser


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        backend = get_backend(args.platform)
        if args.command == "list":
            networks = backend.list_networks(include_passwords=args.show_passwords)
            if args.json:
                print(
                    json.dumps(
                        [_record(item, args.show_passwords) for item in networks],
                        indent=2,
                        ensure_ascii=False,
                    )
                )
            else:
                _print_table(networks, reveal=args.show_passwords)
            return 0

        network = backend.get_network(args.ssid)
        if args.json:
            print(json.dumps(_record(network, True), indent=2, ensure_ascii=False))
        elif network.password is not None:
            print(network.password)
        else:
            raise WifiPasswordError(network.error or "No password is stored for this network")
        return 0
    except WifiPasswordError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
