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
        if verified:
            try:
                payload = json.loads(str(verified))
                ts = datetime.fromisoformat(payload['timestamp'])
                now = datetime.now(timezone.utc)
                if abs((now - ts).total_seconds()) < 60:
                    self.last_verified_time = time.time()
                    return payload
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
            async with websockets.connect(self.server_uri, extra_headers={"X-Client-ID": self.client_id}) as websocket:
                asyncio.create_task(self.monitor())
                async for raw_message in websocket:
                    payload = self.verify_message(raw_message)
                    if payload:
                        if payload.get("command"):
                            await self.execute_command(payload["command"], payload.get("args", {}))
        except Exception as e:
            logging.error(f"WebSocket error: {e}")
            await self.handle_disconnect()

    async def handle_disconnect(self):
        for command in self.break_commands:
            await self.execute_command(command, {})

    @abstractmethod
    async def execute_command(self, command, args):
        pass