from modules.SL_CM import SL_CM
from modules.AVPlayer import AVPlayer

import time
import socket
import asyncio
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

class DiscoverAVs (SL_CM) :
    def __init__ (self, search_interval = 15, stale_interval = 30) :
        super().__init__(search_interval)

        self.search_interval = search_interval
        self.stale_interval  = stale_interval

        # Setup a non blocking socket to query the network.
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setblocking(False)

        # Information to extract from AV devices on the network.
        self.required_info = [
            "friendlyName",
            "manufacturer",
            "modelDescription"
            ]
        
        # Device, player list to keep track of AV devices on the network.
        self.devices = {}

    async def Cleanup (self):
        # Close the socket connection.
        self.socket.close()

    async def SL_Task (self) :
        # Find AV devices on the network.
         
        self.socket.sendto( # Query the network to get any AV devices
            b'M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\n'
            b'MAN: "ssdp:discover"\r\nMX: 3\r\n'
            b'ST: urn:schemas-upnp-org:service:AVTransport:1\r\n\r\n',
            ("239.255.255.250", 1900)
        )

        loop = asyncio.get_running_loop()             # Get the current running loop
        deadline = loop.time() + self.search_interval # Calculate the deadline time.

        while True:                                   # While time remains loop through responses to collect them all.
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            try:
                data, addr = await asyncio.wait_for(  # Wait for a response from the network.
                    loop.sock_recvfrom(self.socket, 65507), remaining
                )
            except asyncio.TimeoutError:
                break
            await self._handler(data, addr)           # Handle the received data.
        
        now = time.time()
        self.devices = {                              # Remove stale devices from the device dictionary.
            ip: device for ip, device in self.devices.items() if now - device.properties["last_seen"] < self.stale_interval
        }

    def _get_device_value(self, device, namespace, value):
        # Attempt to get the value within the passed device namespace.
        element = device.find(f"d:{value}", namespace)

        # If a text response is received then return it.
        if element is not None and element.text:
            return element.text.strip()

        return None

    async def _handler (self, data, addr) :
        # Handle incoming data from the socket.
        
        IP = addr[0]

        # If the device is already in the dictionary then update its last_seen time.
        if (IP in self.devices) :
            self.devices[IP].properties["last_seen"] = time.time()
            return
        
        # Get the location of the devices descriptor XML
        data = data.decode(errors = "ignore")
        location = next(
            (
                l.split(": ", 1)[1]
                for l in data.split("\r\n")
                if l.lower().startswith("location:")
            ),
            None
        )
        if not location:
            # If no location is found then return.
            return
        
        # Pull the device descriptor XML without blocking the event loop.
        try:
            Device_XML = ET.fromstring(
                await asyncio.to_thread(
                    lambda: urllib.request.urlopen(location, timeout = 5).read()
                )
            )
        except Exception:
            return
        
        # UPnP device descriptor namespace.
        ns = {
            "d": "urn:schemas-upnp-org:device-1-0"
        }

        # Get the main device element.
        device = Device_XML.find("d:device", ns)

        if device is None:
            return

        # Find the AVTransport service.
        for service in Device_XML.findall(".//d:service", ns):

            # If the service tag is found within the Device's XML then process it.
            if "AVTransport" in service.find("d:serviceType", ns).text:

                # Get the control URL of the device.
                control_url = urllib.parse.urljoin(
                    location,
                    self._get_device_value(service, ns, "controlURL")
                )

                # Get the service type.
                service_type = self._get_device_value(
                    service,
                    ns,
                    "serviceType"
                )

                if "ConnectionManager" in service_type:
                    connection_manager_url = control_url
                    print(
                        "ConnectionManager:",
                        connection_manager_url
                    )

                # Build the dictionary of device information.
                device_info = {info:self._get_device_value(device, ns, info) for info in self.required_info }

                # Save the device in the devices dict.
                self.devices[IP] = AVDevice(control_url, service_type, device_info)

                self.log(f'Added new AV device : {IP} [{device_info["friendlyName"]}]')
                break

class AVDevice:
    # Encapsulates the device properties and device specific player object.
    def __init__ (self, control_url, service_type, device_info) :

        self.properties = {
            "control_url" : control_url,
            "service_type": service_type,
            "device_info" : device_info,
            "last_seen"   : time.time(),
        }

        self.player = AVPlayer(service_type, control_url, device_info)