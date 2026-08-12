#!/usr/bin/env python3
"""
fake_tv.py - Emulates a minimal DLNA/UPnP AVTransport renderer so you can
test discover_tvs.py without a real TV.

It does two things:
  1. Serves a UPnP device description XML over HTTP.
  2. Listens for SSDP M-SEARCH requests and replies with a LOCATION
     header pointing at that XML - exactly what a real TV does.
"""

import http.server
import socket
import struct
import threading

SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900
HTTP_PORT = 8899

DEVICE_DESCRIPTION_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<root xmlns="urn:schemas-upnp-org:device-1-0">
  <device>
    <deviceType>urn:schemas-upnp-org:device:MediaRenderer:1</deviceType>
    <friendlyName>Fake Test TV</friendlyName>
    <manufacturer>Test</manufacturer>
    <modelName>FakeRenderer</modelName>
    <UDN>uuid:12345678-1234-1234-1234-123456789abc</UDN>
    <serviceList>
      <service>
        <serviceType>urn:schemas-upnp-org:service:AVTransport:1</serviceType>
        <serviceId>urn:upnp-org:serviceId:AVTransport</serviceId>
        <controlURL>/AVTransport/control</controlURL>
        <eventSubURL>/AVTransport/event</eventSubURL>
        <SCPDURL>/AVTransport/scpd.xml</SCPDURL>
      </service>
    </serviceList>
  </device>
</root>
"""


class DescriptionHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/description.xml":
            self.send_response(200)
            self.send_header("Content-Type", "text/xml")
            self.send_header("Content-Length", str(len(DEVICE_DESCRIPTION_XML)))
            self.end_headers()
            self.wfile.write(DEVICE_DESCRIPTION_XML)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        print("[http] " + (fmt % args))


def start_http_server():
    server = http.server.ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), DescriptionHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Serving device description on http://0.0.0.0:{HTTP_PORT}/description.xml")
    return server


def get_local_ip():
    """Best-effort local LAN IP (the one your Pi would actually reach)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # doesn't send anything, just picks a route
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def listen_for_search(local_ip):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.bind(("", SSDP_PORT))

    # Join the multicast group - M-SEARCH goes to 239.255.255.250, not to
    # our own unicast IP, so without this the OS just drops those packets.
    mreq = struct.pack("4sl", socket.inet_aton(SSDP_ADDR), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    location = f"http://{local_ip}:{HTTP_PORT}/description.xml"
    print(f"Listening for SSDP M-SEARCH on {SSDP_ADDR}:{SSDP_PORT}")
    print(f"Will respond with LOCATION: {location}\n")

    while True:
        data, addr = sock.recvfrom(65507)
        text = data.decode(errors="ignore")
        if not text.splitlines() or "M-SEARCH" not in text.splitlines()[0]:
            continue  # ignore anything that isn't a search request

        print(f"Got M-SEARCH from {addr[0]}:{addr[1]}, replying...")
        response = (
            "HTTP/1.1 200 OK\r\n"
            f"LOCATION: {location}\r\n"
            "CACHE-CONTROL: max-age=1800\r\n"
            "EXT:\r\n"
            "SERVER: FakeTV/1.0 UPnP/1.0\r\n"
            "ST: urn:schemas-upnp-org:service:AVTransport:1\r\n"
            "USN: uuid:12345678-1234-1234-1234-123456789abc::"
            "urn:schemas-upnp-org:service:AVTransport:1\r\n"
            "\r\n"
        ).encode()
        sock.sendto(response, addr)


if __name__ == "__main__":
    ip = get_local_ip()
    print(f"Detected local IP: {ip}")
    start_http_server()
    try:
        listen_for_search(ip)
    except KeyboardInterrupt:
        print("\nStopped.")