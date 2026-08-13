import asyncio
import socket
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

from .AVPlayer import AVPlayer

class DiscoverAVs_Instance_Error (Exception) :
    def __init__ (self) :
        super().__init__("Only a single instance of DiscoverAVs should exist at once.")

class DiscoverAVs:
    """
    Discover AV devices on a local network.
    """

    instance_created = False

    def __init__(self, search_interval=30, stale_after=60):
        # Firstly check whether an instance is running so we dont accidentally create more than one.
        if (DiscoverAVs.instance_created) :
            raise DiscoverAVs_Instance_Error()

        # Create a socket object and set it to non blocking to search for AV devices on the network.
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)

        self.search_interval = search_interval
        self.stale_after = stale_after

        self.required_device_info = ["friendlyName", "manufacturer", "modelDescription"]
        self.devices = {}
        self._task = None

        DiscoverAVs.instance_created = True


    def start(self):
        """
        Start the discovery running in an endless loop.
        """
        self._task = asyncio.create_task(self._Discoverer())


    def stop (self):
        """
        Stop the discovery loop and close the socket.
        """
        if self._task:
            self._task.cancel()
        self.sock.close()


    async def _Discoverer(self):
        """
        Discover AV devices on the network.
        """
        
        # Get the current event loop.
        loop = asyncio.get_event_loop()

        while True:
            # Continuously send the search criteria to the network.
            self.sock.sendto(
                b'M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\n'
                b'MAN: "ssdp:discover"\r\nMX: 3\r\n'
                b'ST: urn:schemas-upnp-org:service:AVTransport:1\r\n\r\n',
                ("239.255.255.250", 1900)
            )

            # Calculate the time spent searching the network and waiting for replies.
            deadline = loop.time() + self.search_interval

            # Whilst the current loop time is less than the deadline time, keep searching.
            while loop.time() < deadline:
                try:
                    # Wait for a response from the network.
                    data, addr = await asyncio.wait_for(
                        loop.sock_recvfrom(self.sock, 65507), deadline - loop.time()
                    )
                except asyncio.TimeoutError:
                    # If the connection times out then stop the loop.
                    break

                # Pass any received data to the handler.
                await self._handler(data, addr)

            # Clear out any devices that havent registered a response within the stale_after time.
            now = time.time()
            self.devices = {ip: d for ip, d in self.devices.items()
                             if now - d["last_seen"] < self.stale_after}
            
    
    def _get_device_value(self, device, namespace, value):
        """
        Extract values from a device descriptor.
        """
        # Attempt to get the value within the passed device namespace.
        element = device.find(f"d:{value}", namespace)

        # If a text response is received then return it.
        if element is not None and element.text:
            return element.text.strip()

        return None
            

    async def _handler(self, data, addr):
        """
        Handle data from the discoverer.
        """

        # Get the IP address of the device.
        ip = addr[0]

        # Update the last seen time and return if the device has already been found.
        if ip in self.devices:
            self.devices[ip]["last_seen"] = time.time()
            return

        # Get the location of the device descriptor XML file.
        text = data.decode(errors="ignore")
        location = next(
            (
                l.split(": ", 1)[1]
                for l in text.split("\r\n")
                if l.lower().startswith("location:")
            ),
            None
        )

        # If no location is found then return.
        if not location:
            return

        # Pull the device descriptor XML without blocking the asyncio event loop.
        try:
            Device_XML = ET.fromstring(
                    await asyncio.to_thread(
                        lambda: urllib.request.urlopen(location, timeout=5).read()
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
                device_info = {info:self._get_device_value(device, ns, info) for info in self.required_device_info }

                # Save the device in the devices dict.
                self.devices[ip] = {
                    "control_url" : control_url,
                    "service_type": service_type,
                    "device_info" : device_info,
                    "player"      : AVPlayer(service_type, control_url),
                    "last_seen"   : time.time()
                    }
                break


# Example use
async def main():
    discoverer = DiscoverAVs(search_interval=15)
    discoverer.start()

    while True:
        await asyncio.sleep(5)
        print("Currently known devices:", discoverer.devices)

if __name__ == "__main__":
    asyncio.run(main())