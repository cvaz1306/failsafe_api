from failsafeapi.client import BaseFailsafeClient
import asyncio

class MyClient(BaseFailsafeClient):
    async def execute_command(self, command, args):
        print(f"Executing command: {command} with args {args}")

client = MyClient("ws://localhost:8765", open("server_pubkey.asc").read(), "client1", break_commands=["shutdown"])
asyncio.run(client.run())