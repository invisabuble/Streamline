import asyncio
import os
from aiohttp import web
from pathlib import Path


from modules.DiscoverAVs import DiscoverAVs
from modules.ListMedia import MediaLibrary


class Streamline:

    def __init__(self, host="0.0.0.0", port=8080):

        self.discoverer = DiscoverAVs()
        self.library = MediaLibrary("./media")

        self.media = self.library.list_files()

        self.host = host
        self.port = port

        self.app = web.Application()
        self.frontend = (
            Path(__file__).parent / "./Frontend"
        ).resolve()

        self.app.router.add_get(
            "/api/devices",
            self.devices
        )

        self.app.router.add_get(
            "/api/library",
            self.library_listing
        )

        self.app.router.add_get(
            "/api/player",
            self.Player
        )

        # Add route for the main page.
        self.app.router.add_get(
            "/",
            lambda request: web.FileResponse(
                self.frontend / "index.html"
            )
        )
        # Serve everything else in Frontend/ (style.css, app.js, images, etc.)
        self.app.router.add_static(
            "/",
            path=self.frontend,
            name="static"
        )

    async def start(self):

        self.discoverer.start()

    async def stop(self):

        await self.discoverer.stop()

    # Frontend Routes.
    
    async def devices (self, request):
        result = []

        for ip, device in self.discoverer.devices.items():

            result.append({
                "ip": ip,
                **device["device_info"]
            })

        return web.json_response(result)
    
    
    async def library_listing(self, request):
        path = request.query.get("path", "")
        entries = self.library.list_files(path)
        return web.json_response(entries)
    
    
    async def Player (self, request) :
        file = request.query.get("file", "")
        print(file)
        return web.json_response("")



async def main():

    server = Streamline(
        port=8080
    )

    await server.start()

    runner = web.AppRunner(server.app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        server.host,
        server.port
    )

    await site.start()

    print("Overseer MKV server running on port 8080")

    try:

        await asyncio.Event().wait()

    finally:

        await server.stop()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())