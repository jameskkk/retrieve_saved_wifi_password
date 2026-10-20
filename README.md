# Saved Wi-Fi Passwords

A small, dependency-free Python CLI for retrieving Wi-Fi credentials saved on the local computer. It supports:

- macOS through Keychain and `networksetup`
- Ubuntu through NetworkManager's `nmcli`
- Windows through the native WLAN API (not localized `netsh` output)

Use it only on a computer and account you are authorized to access. Passwords are sensitive: avoid pasting output into logs, tickets, or shell history.

## Install

Python 3.9 or newer is required.

```bash
python3 -m pip install .
```

For development without installing:

```bash
python3 -m wifi_passwords list
```

## Usage

List saved networks without revealing passwords:

```bash
wifi-passwords list
```

Retrieve one password (the output is only the password, which makes it script-friendly):

```bash
wifi-passwords get "My Wi-Fi"
```

Explicitly show all available passwords:

```bash
wifi-passwords list --show-passwords
```

JSON is also available:

```bash
wifi-passwords list --show-passwords --json
wifi-passwords get "My Wi-Fi" --json
```

## OS notes

### macOS

The first password lookup may display a Keychain access prompt. Choose **Allow** to return that credential. The account must be able to read the corresponding `AirPort network password` item.

### Ubuntu

NetworkManager and `nmcli` are required. Reading secrets for system-wide connections may require an authorized desktop session or elevated privileges. Both the NetworkManager connection name and the actual SSID can be used with `get`.

### Windows

The WLAN service must be running. Windows may require an elevated terminal to retrieve plaintext keys. Open and enterprise-authenticated networks do not have a saved PSK to return.

## Security behavior

- `list` never requests or prints passwords unless `--show-passwords` is present.
- Commands are executed without a shell, so an SSID cannot inject shell syntax.
- The tool never writes credentials to disk or a log.
- A missing password is reported without substituting a misleading blank value.

## Test

```bash
python3 -m unittest discover -s tests -v
```
