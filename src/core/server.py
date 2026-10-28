"""
Asynchronous HTTP and WebSocket server handling WVC receiver protocols,
live HLS streaming, range-request media delivery, and real-time remote control.
"""

import os
import mimetypes
import asyncio
import json
import logging
import threading
from typing import Optional, Set
from aiohttp import web, WSMsgType
from src.core.state import app_state

logger = logging.getLogger(__name__)

# Transparent 1x1 GIF for discovery handshake
GIF_1X1 = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)

# 2x2 GIF beacon indicating active caster (triggers auto-connect on WVC)
GIF_2X2 = (
    b"GIF89a\x02\x00\x02\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x02\x00\x02\x00\x00\x02\x02L\x01\x00;"
)


class CasterServer:
    """Manages the aiohttp web server and WebSocket broadcaster in a dedicated thread."""

    def __init__(self, host: str = "0.0.0.0", port: int = 30001):
        self.host = host
        self.port = port
        self.web_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "receiver_web"))
        self.temp_hls_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "temp_hls"))

        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._active_websockets: Set[web.WebSocketResponse] = set()

    def _setup_routes(self, app: web.Application):
        # 0. Global OPTIONS Preflight Handler for TVs
        app.router.add_route("OPTIONS", "/{tail:.*}", self._handle_options)

        # 1. Web Receiver entry points
        app.router.add_get("/", self._handle_index_redirect)
        app.router.add_get("/web-receiver/", self._handle_index_redirect)
        app.router.add_get("/web-receiver/index.html", self._handle_serve_receiver_file)
        app.router.add_get("/web-receiver/player.js", self._handle_serve_receiver_file)
        app.router.add_get("/web-receiver/style.css", self._handle_serve_receiver_file)
        app.router.add_get("/web-receiver/hls.min.js", self._handle_serve_receiver_file)

        # 2. WVC Discovery Beacons
        app.router.add_get("/web-receiver/discover.gif", self._handle_discover_gif)
        app.router.add_get("/web-receiver-io/cast2tv.gif", self._handle_beacon_gif)
        app.router.add_post("/web-receiver-io/connect", self._handle_receiver_connect)
        app.router.add_get("/web-receiver-io/longPoll", self._handle_long_poll)

        # 3. Real-time WebSocket Control
        app.router.add_get("/ws", self._handle_websocket)

        # 4. Live HLS Streaming
        app.router.add_get("/live/stream.m3u8", self._handle_hls_playlist)
        app.router.add_get(r"/live/{segment:.*\.ts}", self._handle_hls_segment)

        # 5. Local Media Streaming (with HTTP 206 Range support)
        app.router.add_get("/media/stream", self._handle_media_stream)
        app.router.add_get("/media/subtitle.vtt", self._handle_subtitle)

        # 6. Status API
        app.router.add_get("/api/status", self._handle_api_status)

    async def _handle_options(self, request: web.Request):
        return web.Response(
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
            }
        )

    async def _handle_long_poll(self, request: web.Request):
        return web.json_response({"status": "idle"}, headers={"Access-Control-Allow-Origin": "*"})

    async def _handle_index_redirect(self, request: web.Request):
        return web.HTTPFound("/web-receiver/index.html")

    async def _handle_serve_receiver_file(self, request: web.Request):
        filename = os.path.basename(request.path)
        filepath = os.path.join(self.web_root, filename)
        if not os.path.isfile(filepath):
            return web.HTTPNotFound(text="File not found")
        content_type, _ = mimetypes.guess_type(filepath)
        return web.FileResponse(filepath, headers={"Content-Type": content_type or "application/octet-stream"})

    async def _handle_discover_gif(self, request: web.Request):
        return web.Response(
            body=GIF_1X1,
            content_type="image/gif",
            headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "no-cache"},
        )

    async def _handle_beacon_gif(self, request: web.Request):
        client_ip = request.remote
        logger.info(f"Received TV beacon from {client_ip}")
        return web.Response(
            body=GIF_2X2,
            content_type="image/gif",
            headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "no-cache"},
        )

    async def _handle_receiver_connect(self, request: web.Request):
        client_ip = request.remote
        try:
            data = await request.json()
            receiver_info = data.get("receiver", {})
            label = receiver_info.get("label", "Unknown TV")
            logger.info(f"TV connected via HTTP POST: {label} ({client_ip})")
            app_state.set_tv_connected(True, client_ip, label)
        except Exception:
            app_state.set_tv_connected(True, client_ip, "Smart TV")

        return web.json_response({"status": "ok"}, headers={"Access-Control-Allow-Origin": "*"})

    async def _handle_websocket(self, request: web.Request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        client_ip = request.remote
        user_agent = request.headers.get("User-Agent", "Unknown")
        logger.info(f"WebSocket client connected from {client_ip} ({user_agent})")
        app_state.set_tv_connected(True, client_ip, user_agent)
        self._active_websockets.add(ws)

        # If a stream or media is currently active, notify the new connection
        if app_state.current_mode == "screen_mirroring":
            await ws.send_json({"action": "play_stream", "url": "/live/stream.m3u8", "title": "Ekran Yansıtma"})
        elif app_state.current_mode == "media_casting" and app_state.active_media_path:
            await ws.send_json({
                "action": "play_media",
                "url": "/media/stream",
                "title": app_state.active_media_title,
                "subtitle": "/media/subtitle.vtt" if app_state.active_subtitle_path else None,
            })

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        event = data.get("event")
                        if event == "timeupdate":
                            app_state.update_media_progress(
                                data.get("currentTime", 0.0),
                                data.get("duration", 0.0)
                            )
                        elif event == "ended":
                            logger.info("TV reported media playback ended.")
                            app_state.set_mode("idle")
                        elif event == "error":
                            logger.warning(f"TV reported error: {data.get('message')}")
                    except Exception as e:
                        logger.warning(f"Error handling WS message: {e}")
                elif msg.type == WSMsgType.ERROR:
                    logger.warning(f"WebSocket closed with exception: {ws.exception()}")
        finally:
            self._active_websockets.discard(ws)
            if not self._active_websockets:
                logger.info("All TV WebSocket connections closed.")
                app_state.set_tv_connected(False)

        return ws

    async def _handle_hls_playlist(self, request: web.Request):
        m3u8_path = os.path.join(self.temp_hls_dir, "stream.m3u8")
        if not os.path.isfile(m3u8_path):
            return web.HTTPNotFound(text="Stream not ready yet")
        return web.FileResponse(
            m3u8_path,
            headers={
                "Content-Type": "application/vnd.apple.mpegurl",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Access-Control-Allow-Origin": "*",
            },
        )

    async def _handle_hls_segment(self, request: web.Request):
        segment = request.match_info["segment"]
        segment_path = os.path.join(self.temp_hls_dir, os.path.basename(segment))
        if not os.path.isfile(segment_path):
            return web.HTTPNotFound(text="Segment not found")
        return web.FileResponse(
            segment_path,
            headers={
                "Content-Type": "video/mp2t",
                "Access-Control-Allow-Origin": "*",
            },
        )

    async def _handle_media_stream(self, request: web.Request):
        media_path = app_state.active_media_path
        if not media_path or not os.path.isfile(media_path):
            return web.HTTPNotFound(text="No active media file")

        file_size = os.path.getsize(media_path)
        content_type, _ = mimetypes.guess_type(media_path)
        content_type = content_type or "video/mp4"

        range_header = request.headers.get("Range")
        if range_header:
            # Parse Range: bytes=start-end
            try:
                byte_range = range_header.replace("bytes=", "").split("-")
                start = int(byte_range[0])
                end = int(byte_range[1]) if byte_range[1] else file_size - 1
            except Exception:
                start = 0
                end = file_size - 1

            start = max(0, min(start, file_size - 1))
            end = max(start, min(end, file_size - 1))
            length = end - start + 1

            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(length),
                "Content-Type": content_type,
                "Access-Control-Allow-Origin": "*",
            }

            resp = web.StreamResponse(status=206, headers=headers)
            await resp.prepare(request)

            with open(media_path, "rb") as f:
                f.seek(start)
                remaining = length
                chunk_size = 64 * 1024
                while remaining > 0:
                    read_bytes = min(remaining, chunk_size)
                    chunk = f.read(read_bytes)
                    if not chunk:
                        break
                    await resp.write(chunk)
                    remaining -= len(chunk)

            await resp.write_eof()
            return resp
        else:
            return web.FileResponse(
                media_path,
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Type": content_type,
                    "Access-Control-Allow-Origin": "*",
                },
            )

    async def _handle_subtitle(self, request: web.Request):
        sub_path = app_state.active_subtitle_path
        if not sub_path or not os.path.isfile(sub_path):
            return web.HTTPNotFound(text="No subtitle available")
        return web.FileResponse(
            sub_path,
            headers={
                "Content-Type": "text/vtt; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
            },
        )

    async def _handle_api_status(self, request: web.Request):
        return web.json_response(app_state.to_dict(), headers={"Access-Control-Allow-Origin": "*"})

    def broadcast_command(self, cmd: dict):
        """Dispatches command dictionary to all connected TV WebSocket clients."""
        if not self._loop or not self._active_websockets:
            return

        async def _send_all():
            for ws in list(self._active_websockets):
                if not ws.closed:
                    try:
                        await ws.send_json(cmd)
                    except Exception as e:
                        logger.warning(f"Error sending command to TV: {e}")

        asyncio.run_coroutine_threadsafe(_send_all(), self._loop)

    def start(self):
        """Starts the aiohttp server in a dedicated background thread."""
        def run_server():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            self._app = web.Application()
            self._setup_routes(self._app)

            self._runner = web.AppRunner(self._app)
            self._loop.run_until_complete(self._runner.setup())

            site = web.TCPSite(self._runner, self.host, self.port)
            self._loop.run_until_complete(site.start())
            logger.info(f"Caster HTTP & WebSocket server started at http://{self.host}:{self.port}")

            self._loop.run_forever()

        self._thread = threading.Thread(target=run_server, daemon=True)
        self._thread.start()

    def stop(self):
        """Shuts down the web server cleanly."""
        if self._loop and self._runner:
            async def _cleanup():
                await self._runner.cleanup()
                self._loop.stop()

            asyncio.run_coroutine_threadsafe(_cleanup(), self._loop)
            logger.info("Caster server stopped.")
