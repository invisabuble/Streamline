import asyncio
import os
from aiohttp import web
from pathlib import Path
import socket


from modules.DiscoverAVs import DiscoverAVs
from modules.ListMedia import MediaLibrary


def get_local_ip():
    # Create a UDP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to a dummy address (8.8.8.8 is Google's public DNS)
        # This doesn't actually send packets or require internet access, 
        # it just forces the OS to pick the right network interface.
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except Exception:
        # Fallback if no network interface is active
        local_ip = "127.0.0.1"
    finally:
        s.close()
    return local_ip


class Streamline:

    def __init__(self, host="0.0.0.0", port=8080):

        self.discoverer = DiscoverAVs()
        self.library = MediaLibrary("/mnt")

        self.media = self.library.list_files()

        self.target_device = None

        self.host = host
        self.port = port

        self.app = web.Application()

        self.frontend = (
            Path(__file__).parent / "./Frontend"
        ).resolve()

        self.app.router.add_get(
            "/api/play",
            self.play
        )

        self.app.router.add_get(
            "/api/pause",
            self.pause
        )

        self.app.router.add_get(
            "/api/devices",
            self.devices
        )

        self.app.router.add_get(
            "/api/library",
            self.library_listing
        )

        self.app.router.add_get(
            "/api/set_media_file",
            self.set_media_file
        )

        self.app.router.add_static(
            "/media/",
            path=self.library.root_dir,
            name="media"
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
    
    
    async def set_media_file (self, request) :
        file = request.query.get("file", "")
        device = request.query.get("device", "")

        media_file = f"http://{get_local_ip()}:8080/media/{file}"

        print(media_file)

        self.target_device = self.discoverer.devices[device]["player"]
        await self.target_device.set_uri(media_file)

        print(device, file)
        return web.json_response("")
    

    async def play (self, request) :
        await self.target_device.play()
        return web.json_response("")
    

    async def pause (self, request) :
        await self.target_device.pause()
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