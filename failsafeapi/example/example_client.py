import argparse

from failsafeapi.client import BaseFailsafeClient
import asyncio

class MyClient(BaseFailsafeClient):
    async def execute_command(self, command, args):
        print(f"Executing command: {command} with args {args}")

parser = argparse.ArgumentParser()
parser.add_argument("--server-uri", default="wss://secureservices.criticalfunctions.net/")
parser.add_argument("--public-key", default="server_pubkey.asc")
parser.add_argument("--client-id", default="client1")
parser.add_argument("--break-commands", default="shutdown")
args = parser.parse_args()

client = MyClient(args.server_uri, open(args.public_key).read(), args.client_id, break_commands=[(args.break_commands, {"force": True})])
asyncio.run(client.run())