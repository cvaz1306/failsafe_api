import asyncio
import websockets
import gnupg
import time
import json
import logging
import signal
import argparse
import os
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)

gpg = gnupg.GPG()

CHECK_INTERVAL = 5

class FailsafeServer:
    def __init__(self, private_key_fingerprint, gpg_passphrase=None):
        self.private_key_fingerprint = private_key_fingerprint
        self.clients = {}
        self.gpg_passphrase = gpg_passphrase

    async def handler(self, websocket, path="/"):
        headers = websocket.request.headers
        
        client_id = headers.get("X-Client-ID", str(websocket.remote_address))
        if not client_id:
            await websocket.close()
            return

        self.clients[client_id] = websocket
        logging.info(f"Client {client_id} connected")
        try:
            while True:
                payload = {"timestamp": datetime.now(timezone.utc).isoformat()}
                signed_data = gpg.sign(json.dumps(payload), keyid=self.private_key_fingerprint, passphrase=self.gpg_passphrase)
                if not signed_data:
                    logging.error("Failed to sign timestamp payload")
                    break
                log.info("Preparing to send: payload")
                await websocket.send(str(signed_data))
                await asyncio.sleep(CHECK_INTERVAL)
        except asyncio.CancelledError:
            logging.info(f"Client {client_id} task cancelled")
        except Exception as e:
            logging.warning(f"Client {client_id} disconnected: {e}")
        finally:
            self.clients.pop(client_id, None)

    async def send_command(self, command, args=None, client_id=None):
        args = args or {}
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "command": command,
            "args": args,
        }
        signed_data = gpg.sign(json.dumps(payload), keyid=self.private_key_fingerprint, passphrase=self.gpg_passphrase)
        if not signed_data:
            logging.error("Failed to sign command payload")
            return

        signed_message = str(signed_data)
        targets = [client_id] if client_id else list(self.clients.keys())

        for cid in targets:
            ws = self.clients.get(cid)
            if ws:
                try:
                    await ws.send(signed_message)
                except Exception as e:
                    logging.warning(f"Failed to send to {cid}: {e}")

    async def start(self, host='0.0.0.0', port=8765):
        async with websockets.serve(self.handler, host, port):
            logging.info(f"Server running at ws://{host}:{port}")
            await asyncio.Future()  # Run forever


def main():
    parser = argparse.ArgumentParser(description="Failsafe API system")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser = subparsers.add_parser("serve", help="Run the Failsafe server")
    serve_parser.add_argument("--key-fingerprint", required=True, help="PGP private key fingerprint to sign messages")
    serve_parser.add_argument("--host", default="0.0.0.0", help="WebSocket server host")
    serve_parser.add_argument("--port", type=int, default=8765, help="WebSocket server port")

    args = parser.parse_args()

    if args.command == "serve":
        server = FailsafeServer(args.key_fingerprint)
        asyncio.run(server.start(host=args.host, port=args.port))


if __name__ == "__main__":
    main()