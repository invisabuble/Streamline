import asyncio
from xml.sax.saxutils import escape
import urllib.request
import urllib.error


class AVPlayer:

    def __init__(self, service_type, control_url):
        self.service_type = service_type
        self.control_url = control_url


    async def _soap(self, action, arguments):

        body = f"""<?xml version="1.0"?>
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
        <s:Body>
        <u:{action} xmlns:u="{self.service_type}">
        {arguments}
        </u:{action}>
        </s:Body>
        </s:Envelope>
        """

        headers = {
            "Content-Type": 'text/xml; charset="utf-8"',
            "SOAPAction": f'"{self.service_type}#{action}"'
        }


        def send():

            request = urllib.request.Request(
                self.control_url,
                data=body.encode("utf-8"),
                headers=headers,
                method="POST"
            )

            try:

                response = urllib.request.urlopen(
                    request,
                    timeout=5
                )

                return response.read()


            except urllib.error.HTTPError as error:

                print("TV returned HTTP error:", error.code)

                print(
                    "TV response:",
                    error.read().decode(
                        "utf-8",
                        errors="ignore"
                    )
                )

                raise


        return await asyncio.to_thread(send)


    async def set_uri(self, uri):

        print("Setting TV media URI:", uri)

        escaped_uri = escape(uri)

        metadata = f"""<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">
        <item id="1" parentID="0" restricted="1">
        <dc:title>Movie</dc:title>
        <upnp:class>object.item.videoItem</upnp:class>
        <res protocolInfo="http-get:*:video/x-matroska:*">{escaped_uri}</res>
        </item>
        </DIDL-Lite>"""

        arguments = f"""<InstanceID>0</InstanceID>
        <CurrentURI>{escaped_uri}</CurrentURI>
        <CurrentURIMetaData>{escape(metadata)}</CurrentURIMetaData>"""

        await self._soap(
            "SetAVTransportURI",
            arguments
        )

        print("TV accepted media URI.")


    async def play(self):
        # Send the play command to the AV device.

        ret = ""

        try :
            await self._soap(
                "Play",
                "<InstanceID>0</InstanceID><Speed>1</Speed>"
            )
            ret = "Playing..."

        except Exception as e:
            ret = f"Failed to play : {e}"

        return ret


    async def pause(self):
        # Send the pause command to the AV device.

        ret = ""

        try:
            await self._soap(
                "Pause",
                "<InstanceID>0</InstanceID>"
            )
            ret = "Paused."

        except Exception as e:
            ret = f"Failed to pause : {e}"

        return ret