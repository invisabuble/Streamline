from modules.DiscoverAVs import DiscoverAVs
from modules.FileManager import FileManager
from modules.DriveManager import DriveManager

import signal
import asyncio
import functools
import urllib.parse
import aiohttp_cors
from aiohttp import web


def Streamline_route(method):
    # Custom decorator to set the last command status so the front can determine if an error occured.
    @functools.wraps(method)
    async def wrapper(self, request):
        try:
            response = await method(self, request)
            self.last_command_status = "OK"
            return response
        except Exception as e:
            self.last_command_status = "KO"
            return web.json_response(
                {"error": str(e)}, status=500
            )
    return wrapper


class Streamline:

    def __init__(self, host="0.0.0.0", port=8080, media_directory="/mnt/"):
        self.host     = host
        self.port     = port
        self.mdir     = media_directory
        self.local_ip = "192.168.0.102"

        # Add the DLNA header middleware.
        self.app = web.Application(
            middlewares=[self.dlna_headers]
        )

        # Variables to hold the context managers.
        self.Discoverer = None
        self.FileManager = None
        self.DriveManager = None

        self.last_command_status = None

        self.app.router.add_get(
            "/api/last_cmd_stat",
            self.last_cmd_stat
        )

        self.app.router.add_get(
            "/api/devices",
            self.get_device_list
        )

        self.app.router.add_get(
            "/api/get_file_list",
            self.get_file_list
        )

        self.app.router.add_get(
            "/api/set_target",
            self.set_target
        )

        self.app.router.add_get(
            "/api/play_target",
            self.play_target
        )

        self.app.router.add_get(
            "/api/pause_target",
            self.pause_target
        )

        self.app.router.add_get(
            "/api/stop_target",
            self.stop_target
        )

        self.cors = aiohttp_cors.setup(self.app, defaults={
            "http://streamline.local": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*",
            )
        })

        for route in list(self.app.router.routes()) :
            self.cors.add(route)

        # Host the media folder over http so the AV devices on the network can access the files.
        self.app.router.add_static(
            self.mdir,
            path=self.mdir,
            name="media"
        )

    @web.middleware
    async def dlna_headers(self, request, handler):
        # Allow aiohttp's normal handler to generate the response first.
        response = await handler(request)

        # Only add these headers to files served from the media directory.
        if request.path.startswith(self.mdir):

            response.headers["contentFeatures.dlna.org"] = (
                "DLNA.ORG_OP=11;"
                "DLNA.ORG_PS=2,4;"
                "DLNA.ORG_FLAGS=01700000000000000000000000000000"
            )

            response.headers["transferMode.dlna.org"] = "Streaming"

        return response

    @Streamline_route
    async def last_cmd_stat (self, request) :
        return web.json_response(
            {"Status":self.last_command_status}
        )
    
    @Streamline_route
    async def get_device_list (self, request) :
        if self.Discoverer is None:
            return web.json_response({"Error":"No AV Discoverer is Active."})
        # Pull all of the device properties from the discoverer.
        ret = {ip:device.properties for ip, device in self.Discoverer.devices.items()}
        return web.json_response(ret)
    
    @Streamline_route
    async def get_file_list (self, request) :
        if self.FileManager is None :
            return web.json_response({"Error":"No File Manager is Active."})
        return web.json_response(self.FileManager.hierarchy)
    
    def _get_request_variable (self, request, variables) :
        # Extract multiple variables from a request.
        return [request.query.get(variable, "") for variable in variables]

    @Streamline_route
    async def set_target (self, request) :
        # Set a target media file on a target device.

        # Pull the target file and target device from the request.
        file, device, title = self._get_request_variable(request, ["file", "device", "title"])

        encoded_file = urllib.parse.quote(file, safe="/")
        media_file = f"http://{self.local_ip}:{self.port}{self.mdir}{encoded_file}"

        # Pull the target device from the devices list.
        target_device = self.Discoverer.devices[device]

        print(f"Playing {media_file} on {target_device.properties["device_info"]["friendlyName"]}")
        # Set the target URL on the AV device.
        await target_device.player.set_uri (media_file, f"{self.mdir}{file}", title)

        return web.json_response("")
    
    @Streamline_route
    async def play_target (self, request) :
        # Play the set media file on the target device.
        device_ip, speed = self._get_request_variable(request, ["device", "speed"])
        target_device = self.Discoverer.devices[device_ip]

        # Press 'play' on the device
        ret = await target_device.player.send_command(
            "Play",
            f"<InstanceID>0</InstanceID><Speed>{speed}</Speed>"
        )

        return web.json_response(ret)
    
    @Streamline_route
    async def pause_target (self, request) :
        # Pause the set media file on the target device.
        device_ip = self._get_request_variable(request, ["device"])[0]
        target_device = self.Discoverer.devices[device_ip]

        # Press 'pause' on the device
        ret = await target_device.player.send_command(
            "Pause",
            "<InstanceID>0</InstanceID>"
        )

        return web.json_response(ret)
    
    @Streamline_route
    async def stop_target (self, request) :
        device_ip = self._get_request_variable(request, ["device"])[0]
        target_device = self.Discoverer.devices[device_ip]

        # Stop playback on the target device.
        ret = await target_device.player.send_command(
            "Stop",
            "<InstanceID>0</InstanceID>"
        )

        return web.json_response(ret)


async def main () :

    # Define variables needed for the API.
    MEDIA_DIR = "/mnt/"
    API_PORT  = 8080

    # Setup and run the API.
    API = Streamline(port=API_PORT, media_directory=MEDIA_DIR)
    runner = web.AppRunner(API.app)
    await runner.setup()

    site = web.TCPSite (
        runner,
        API.host,
        API.port
    )

    await site.start()

    print(f"Streamline API running on port {API.port}. Using media directory : {API.mdir}.")

    # Setup a stop event thats triggered by SIGTERM/SIGINT, so shutdown
    # goes through the normal async with exit path instead of being killed outright.
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, stop_event.set)
    loop.add_signal_handler(signal.SIGINT, stop_event.set)

    # Setup the context managers inside of the API.
    async with (DiscoverAVs() as API.Discoverer,
                FileManager(MEDIA_DIR) as API.FileManager, 
                DriveManager(MEDIA_DIR) as API.DriveManager):
        await stop_event.wait()
    
    await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())