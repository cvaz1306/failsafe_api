# FailsafeAPI

FailsafeAPI is a secure command and monitoring framework using signed WebSocket messages over TLS and a RESTful control API. It is designed to ensure remote actions are authenticated and failsafe behaviors are automatically triggered when connectivity is lost.

## Features

- WebSocket-based signed command delivery
- REST API interface for issuing commands
- PGP-based message signing and verification
- Failsafe actions on connection loss
- Extendable client-side command handlers

---

## Installation

```bash
git clone https://github.com/yourusername/failsafeapi.git
cd failsafeapi
python3 -m venv venv
source venv/bin/activate
pip install -e .
````

---

## Setup PGP Keys

Both client and server require a GPG key pair (server) or public key (client).

### Generate Keys (if needed):

```bash
gpg --full-generate-key
gpg --list-keys
```

Get your key fingerprint from the output.

---

## Running the Server

### Start the WebSocket + REST API server:

```bash
python3 -m failsafeapi serve --key-fingerprint <YOUR_PRIVATE_KEY_FPR> --host 0.0.0.0 --port 8765 --http-port 8080
```

### REST API Usage

Send a command via `POST` to:

```
http://<server-host>:8080/send
```

#### Example Payload:

```json
{
  "command": "shutdown",
  "args": {
    "delay": 5
  },
  "client_id": "my-client-123"
}
```

All arguments must be passed in base64-encoded JSON format (if required by your setup).

---

## Running the Client

Subclass `BaseFailsafeClient` to define your own command handler:

```python
class MyClient(BaseFailsafeClient):
    async def execute_command(self, command, args):
        if command == "shutdown":
            print("Shutting down...")
            # os.system("shutdown now") or something similar
        else:
            print(f"Unknown command: {command}")
```

Run your client:

```bash
python3 -m failsafeapi.example.example_client
```

---

## Failsafe Trigger

If the client loses connection or does not receive a signed heartbeat within `FAILSAFE_TIMEOUT` seconds (default: 15), it will:

1. Log the connection loss
2. Execute the list of preconfigured `break_commands`

You can define `break_commands` as a list of `(command, args)` tuples when initializing your client.

---

## Project Structure

```
failsafeapi/
├── __init__.py
├── server.py           # WebSocket + REST API server
├── client.py           # BaseFailsafeClient class
└── example/
    └── example_client.py  # Sample implementation
```

---

## Testing

You can test the system locally with:

* A server running on `localhost:8765`
* A client connecting with the corresponding fingerprint
* REST `curl` commands to trigger actions

---

## Security Notes

* All messages are signed using PGP; the client verifies them before executing any actions.
* Time-based freshness is enforced using ISO timestamps in UTC.
* Failsafe logic is triggered if no verified messages are received within the timeout window.

---

## TODO

* [ ] TLS encryption support for WebSocket/HTTP
* [ ] Auth tokens for REST interface
* [ ] Message replay protection (nonce or sequence ID)
* [ ] Optional message encryption (not just signing)

---

## 📄 License

MIT License. Feel free to use and modify.