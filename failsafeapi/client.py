import asyncio
import websockets
import gnupg
import time
import json
import logging
from datetime import datetime, timezone
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO)

gpg = gnupg.GPG()

CHECK_INTERVAL = 5
FAILSAFE_TIMEOUT = 15

class BaseFailsafeClient(ABC):
    def __init__(self, server_uri, public_key, client_id, break_commands=None):
        self.server_uri = server_uri
        self.public_key = public_key
        self.client_id = client_id
        self.break_commands = break_commands or []
        self.last_verified_time = time.time()
        self.running = True

    def import_key(self):
        gpg.import_keys(self.public_key)

    def verify_message(self, message):
        verified = gpg.verify(message)
        if not verified:
            logging.error("Signature verification failed")
            return None

        # Extract the signed plaintext from the message:
        # The cleartext is inside the signature object as .data or .data.decode()
        # But gnupg's verify() result does not provide that,
        # so you need to parse manually or get the cleartext by other means.

        # Since gnupg module does not expose the plaintext from verify(),
        # and decrypt() fails because the message isn't encrypted,
        # you need to extract the cleartext by stripping the signature block.

        # Here is a simple approach using gnupg's "verify" with a temp file:

        import tempfile

        with tempfile.NamedTemporaryFile("w+", delete=True) as f:
            f.write(message)
            f.flush()
            # Run gpg --verify --status-fd=1 on the file to parse status and get plaintext
            # This is complex; easier is to ask server to send signed JSON *inside* signed message

        # Or better: change server to send signed *detached* signatures, or send JSON separately.

        # For now, as a workaround, try to verify *and* parse the message as JSON directly:
        try:
            # The message looks like:
            # -----BEGIN PGP SIGNED MESSAGE-----
            # Hash: SHA256
            #
            # <actual JSON here>
            # -----BEGIN PGP SIGNATURE-----
            # ...
            # -----END PGP SIGNATURE-----
            # So parse out the signed JSON by removing the PGP armor headers

            lines = message.splitlines()
            # find the first blank line after 'Hash: ...'
            blank_index = None
            for i, line in enumerate(lines):
                if line.strip() == "":
                    blank_index = i
                    break
            if blank_index is None:
                logging.error("Malformed signed message")
                return None

            # Extract the signed content between blank line and signature header
            signed_content_lines = []
            for line in lines[blank_index+1:]:
                if line.startswith("-----BEGIN PGP SIGNATURE-----"):
                    break
                signed_content_lines.append(line)
            signed_content = "\n".join(signed_content_lines)

            payload = json.loads(signed_content)
            ts = datetime.fromisoformat(payload['timestamp'])
            now = datetime.now(timezone.utc)
            if abs((now - ts).total_seconds()) < 60:
                self.last_verified_time = time.time()
                return payload
            else:
                logging.error("Timestamp difference too large")
        except Exception as e:
            logging.error(f"Payload error: {e}")
        return None




    async def monitor(self):
        while self.running:
            if time.time() - self.last_verified_time > FAILSAFE_TIMEOUT:
                logging.warning("Connection lost. Executing failsafe.")
                await self.handle_disconnect()
                break
            await asyncio.sleep(CHECK_INTERVAL)

    async def run(self):
        self.import_key()
        try:
            async with websockets.connect(self.server_uri, additional_headers={"X-Client-ID": self.client_id}) as websocket:
                logging.info("Connected to server")

                while self.running:
                    try:
                        # Timeout after FAILSAFE_TIMEOUT + some buffer
                        raw_message = await asyncio.wait_for(websocket.recv(), timeout=FAILSAFE_TIMEOUT + 5)
                        payload = self.verify_message(raw_message)
                        if payload:
                            if payload.get("command"):
                                await self.execute_command(payload["command"], payload.get("args", {}))
                    except asyncio.TimeoutError:
                        logging.warning("No messages received in timeout window. Executing failsafe.")
                        await self.handle_disconnect()
                        break
                    except websockets.exceptions.ConnectionClosedError as e:
                        logging.warning(f"Connection closed: {e}")
                        await self.handle_disconnect()
                        break
                    except Exception as e:
                        logging.error(f"Unexpected error: {e}")
                        await self.handle_disconnect()
                        break
        except Exception as e:
            logging.error(f"WebSocket connection error: {e}")
            await self.handle_disconnect()


    async def handle_disconnect(self):
        print("Executing failsafe commands")
        for command, args in self.break_commands:
            await self.execute_command(command, args)

    @abstractmethod
    async def execute_command(self, command, args):
        pass