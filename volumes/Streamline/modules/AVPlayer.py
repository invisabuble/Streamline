import os
import asyncio
import subprocess
import urllib.error
import urllib.request
from xml.sax.saxutils import escape

VIDEO_MIME_TYPES = {
    ".mkv": "video/x-matroska",
    ".mp4": "video/mp4",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
}

class AVPlayer : 

    def __init__ (self, service_type, control_url, device_info) :
        self.service_type = service_type
        self.control_url  = control_url
        self.device_info  = device_info

    async def _SOAP (self, action, arguments) :
        # Simple Object Access Protocol.

        # Construct the body of POST request.
        body = f"""<?xml version="1.0"?>
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
        <s:Body>
        <u:{action} xmlns:u="{self.service_type}">
        {arguments}
        </u:{action}>
        </s:Body>
        </s:Envelope>
        """

        # Construct the headers of the POST request.
        headers = {
            "Content-Type": 'text/xml; charset="utf-8"',
            "SOAPAction": f'"{self.service_type}#{action}"'
        }

        # Define a helper function here so we can later await this method in an async thread.
        def send():

            # Define the request.
            request = urllib.request.Request(
                self.control_url,
                data=body.encode("utf-8"),
                headers=headers,
                method="POST"
            )

            try:
                # Attempt to POST.
                response = urllib.request.urlopen(
                    request,
                    timeout=5
                )
                return response.read()

            except urllib.error.HTTPError as error:
                print(f"Response: {error.read().decode("utf-8",errors="ignore")}")
                raise

        # Await the POST request.
        return await asyncio.to_thread(send)
    

    def _guess_mime_type(self, uri):
        # Guess the mime type of the passed file by determining what it endswith.
        # Falls back to MKV if nothing is returned.
        for ext, mime in VIDEO_MIME_TYPES.items():
            if uri.lower().endswith(ext):
                return mime
        return "video/x-matroska"
    

    async def _get_media_info (self, file_path):
        # Get the duration and size of a media file.

        result = await asyncio.to_thread(
            subprocess.run, [
                "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
                ],
            capture_output=True, text=True, check=True
        )

        # Convert the seconds to a standarf format.
        seconds = float(result.stdout.strip())

        h, remainder = divmod(int(seconds), 3600)
        m, s = divmod(remainder, 60)
        ms = int((seconds - int(seconds)) * 1000)

        duration =  f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

        # Get the file size in bytes.
        size = await asyncio.to_thread(os.path.getsize, file_path)

        return duration, size
    
    
    async def set_uri(self, uri, local_path, title = ""):
        # Send the file URL to the AV device.

        print(f"Setting media URI: {uri}")

        # Create the escaped URI and guess the mime type.
        escaped_uri = escape(uri)
        mime_type = self._guess_mime_type(uri)

        # Get information associated with the media file.
        duration, size = await self._get_media_info(local_path)

        # If the title string is empty set it to 'Movie'
        if (title == "") :
            title = "Movie"

        # Create the XML metadata.
        metadata = f"""<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">
        <item id="1" parentID="0" restricted="1">
        <dc:title>{title}</dc:title>
        <upnp:class>object.item.videoItem</upnp:class>
        <res protocolInfo="http-get:*:{mime_type}:DLNA.ORG_OP=11;DLNA.ORG_PS=2,4;DLNA.ORG_FLAGS=01700000000000000000000000000000" duration="{duration}" size="{size}">{escaped_uri}</res>
        </item>
        </DIDL-Lite>"""

        # Create the XML arguments using the metadata and escaped uri.
        arguments = f"""<InstanceID>0</InstanceID>
        <CurrentURI>{escaped_uri}</CurrentURI>
        <CurrentURIMetaData>{escape(metadata)}</CurrentURIMetaData>"""

        # Send the arguments to the AV device.
        await self._SOAP (
            "SetAVTransportURI",
            arguments
        )

        print("Device accepted media URI.")


    async def send_command (self, action, arguments) :
        # Send a command to the AV device.
        ret = ""

        try :
            await self._SOAP(
                action,
                arguments
            )

        except Exception as e :
            ret = f"Command failed : {e}"

        return ret