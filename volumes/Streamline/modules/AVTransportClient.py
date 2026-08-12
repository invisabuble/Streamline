import asyncio
import urllib.request
import xml.etree.ElementTree as ET

AVTRANSPORT_URN = "urn:schemas-upnp-org:service:AVTransport:1"


class AVTransportClient:
    def __init__(self, control_url):
        self.control_url = control_url

    async def set_uri(self, file_url, title, mime_type):
        didl = (
            '<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">'
            '<item id="0" parentID="0" restricted="0">'
            f"<dc:title>{self._escape(title)}</dc:title>"
            "<upnp:class>object.item.videoItem</upnp:class>"
            f'<res protocolInfo="http-get:*:{mime_type}:*">{self._escape(file_url)}</res>'
            "</item></DIDL-Lite>"
        )
        args = (
            "<InstanceID>0</InstanceID>"
            f"<CurrentURI>{self._escape(file_url)}</CurrentURI>"
            f"<CurrentURIMetaData>{self._escape(didl)}</CurrentURIMetaData>"
        )
        await self._call("SetAVTransportURI", args)

    async def play(self):
        await self._call("Play", "<InstanceID>0</InstanceID><Speed>1</Speed>")

    async def pause(self):
        await self._call("Pause", "<InstanceID>0</InstanceID>")

    async def stop(self):
        await self._call("Stop", "<InstanceID>0</InstanceID>")

    async def get_transport_info(self):
        """Returns e.g. PLAYING / PAUSED_PLAYBACK / STOPPED."""
        raw = await self._call("GetTransportInfo", "<InstanceID>0</InstanceID>")
        state = ET.fromstring(raw).find(".//CurrentTransportState")
        return state.text if state is not None else "UNKNOWN"

    async def get_position_info(self):
        """Returns (current_position, total_duration) as HH:MM:SS."""
        raw = await self._call("GetPositionInfo", "<InstanceID>0</InstanceID>")
        root = ET.fromstring(raw)
        rel_time = root.find(".//RelTime")
        duration = root.find(".//TrackDuration")
        return (
            rel_time.text if rel_time is not None else "?",
            duration.text if duration is not None else "?",
        )

    # -- internals -----------------------------------------------------

    async def _call(self, action, args_xml):
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
            's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            f'<s:Body><u:{action} xmlns:u="{AVTRANSPORT_URN}">{args_xml}</u:{action}></s:Body>'
            "</s:Envelope>"
        ).encode()

        def send():
            req = urllib.request.Request(self.control_url, data=body, method="POST")
            req.add_header("Content-Type", 'text/xml; charset="utf-8"')
            req.add_header("SOAPACTION", f'"{AVTRANSPORT_URN}#{action}"')
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.read()

        return await asyncio.to_thread(send)

    @staticmethod
    def _escape(s):
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )