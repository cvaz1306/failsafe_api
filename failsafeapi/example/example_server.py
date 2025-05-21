import argparse
import os
from failsafeapi.server import FailsafeServer
import asyncio
import websockets
import asyncio
import base64
import json
import logging
from aiohttp import web

class RestFailsafeServer(FailsafeServer):
    def __init__(self, private_key_fingerprint, host='0.0.0.0', ws_port=8765, http_port=8080, gpg_passphrase=None):
        super().__init__(private_key_fingerprint, gpg_passphrase=gpg_passphrase)
        self.host = host
        self.ws_port = ws_port
        self.http_port = http_port
        self._http_runner = None

    async def handle_command(self, request):
        try:
            # Read raw base64-encoded string from POST body
            b64_data = await request.text()
            # Decode base64
            json_str = base64.b64decode(b64_data).decode('utf-8')
            # Parse JSON
            data = json.loads(json_str)

            command = data.get("command")
            args = data.get("args", {})

            if not command:
                return web.Response(status=400, text="Missing 'command' field")

            # Send command to all connected clients
            await self.send_command(command, args)
            return web.Response(status=200, text="Command sent")
        except Exception as e:
            logging.error(f"Error handling REST command: {e}")
            return web.Response(status=500, text=f"Internal server error: {e}")

    async def start_http_server(self):
        app = web.Application()
        app.router.add_post("/command", self.handle_command)
        self._http_runner = web.AppRunner(app)
        await self._http_runner.setup()
        site = web.TCPSite(self._http_runner, '0.0.0.0', self.http_port)
        await site.start()
        logging.info(f"REST API running at http://0.0.0.0:{self.http_port}")

    async def start(self):
        # Start WS server and HTTP server concurrently
        ws_server = websockets.serve(self.handler, self.host, self.ws_port)
        await asyncio.gather(
            ws_server,
            self.start_http_server()
        )
        # keep running forever
        await asyncio.Future()

    async def stop(self):
        if self._http_runner:
            await self._http_runner.cleanup()
def main():
    parser = argparse.ArgumentParser(description="Failsafe API system")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser = subparsers.add_parser("serve", help="Run the Failsafe server")
    serve_parser.add_argument("--key-fingerprint", required=True, help="PGP private key fingerprint to sign messages")
    serve_parser.add_argument("--host", default="0.0.0.0", help="WebSocket server host")
    serve_parser.add_argument("--ws-port", type=int, default=8765, help="WebSocket server port")
    serve_parser.add_argument("--http-port", type=int, default=8080, help="WebSocket server port")
    serve_parser.add_argument("--passphrase-env-var", default="FAILSAFE_GPG_PASSPHRASE", help="Environment variable containing GPG passphrase")

    args = parser.parse_args()

    if args.command == "serve":
        server = RestFailsafeServer(args.key_fingerprint, host=args.host, ws_port=args.ws_port, http_port=args.http_port, gpg_passphrase=os.getenv(args.passphrase_env_var, None))
        asyncio.run(server.start())


if __name__ == "__main__":
    main()
