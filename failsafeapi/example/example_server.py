from failsafeapi.server import FailsafeServer
import asyncio

server = FailsafeServer("<YOUR_KEY_FINGERPRINT>")
asyncio.run(server.start())