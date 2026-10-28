"""
Asynchronous HTTP and WebSocket server handling WVC receiver protocols,
including Smart TV Long-Polling (/web-receiver-io/longPoll), WebSocket (/ws),
live HLS streaming, range-request media delivery, and real-time remote control.
"""

import os
import mimetypes
import asyncio
import json
import logging
import threading
import time
from typing import Optional, Set, List, Dict, Any
from aiohttp import web, WSMsgType
from src.core.state import app_state
from src.utils.network import get_primary_local_ip

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

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, HEAD, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Client-Id, Range",
    "Access-Control-Expose-Headers": "Content-Range, Accept-Ranges, Content-Length",
}


class CasterServer:
    """Manages the aiohttp web server, WVC Smart TV Long-Polling, and WebSocket broadcaster."""

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

        # Smart TV Native WVC Long-Polling Queue & Event
        self._tv_command_queue: List[Dict[str, Any]] = []
        self._tv_poll_event: Optional[asyncio.Event] = None
        self._tv_sent_initial_media: bool = False

    def _get_base_url(self) -> str:
        ip = get_primary_local_ip()
        return f"http://{ip}:{self.port}"

    def _setup_routes(self, app: web.Application):
        # 0. Global OPTIONS Preflight Handler for Smart TVs
        app.router.add_route("OPTIONS", "/{tail:.*}", self._handle_options)

        # 1. WVC Discovery Beacons (Must be registered BEFORE wildcard /web-receiver/{filename})
        app.router.add_get("/web-receiver/discover.gif", self._handle_discover_gif)
        app.router.add_get("/web-receiver-io/cast2tv.gif", self._handle_beacon_gif)
        app.router.add_post("/web-receiver-io/connect", self._handle_receiver_connect)

        # 2. Native WVC Smart TV App Endpoints (/web-receiver-io/*)
        app.router.add_post("/web-receiver-io/request-connection", self._handle_request_connection)
        app.router.add_get("/web-receiver-io/longPoll", self._handle_long_poll)
        app.router.add_post("/web-receiver-io/longPoll", self._handle_long_poll)
        app.router.add_post("/web-receiver-io/state", self._handle_tv_state)
        app.router.add_post("/web-receiver-io/position", self._handle_tv_position)
        app.router.add_post("/web-receiver-io/media", self._handle_tv_media)
        app.router.add_post("/web-receiver-io/error", self._handle_tv_error)
        app.router.add_post("/web-receiver-io/volume", self._handle_tv_volume)
        app.router.add_post("/web-receiver-io/log", self._handle_tv_log)
        app.router.add_post("/web-receiver-io/disconnect", self._handle_tv_disconnect)
        app.router.add_post("/web-receiver-io/deviceInfo", self._handle_tv_device_info)
        app.router.add_post("/web-receiver-io/playNext", self._handle_tv_ok)
        app.router.add_post("/web-receiver-io/playPrevious", self._handle_tv_ok)

        # 3. Web Receiver entry points (for browser / cast2tv.app)
        app.router.add_get("/", self._handle_index_redirect)
        app.router.add_get("/web-receiver/", self._handle_index_redirect)
        app.router.add_get("/web-receiver/{filename:.*}", self._handle_serve_receiver_file)

        # 4. Real-time WebSocket Control (for browser player)
        app.router.add_get("/ws", self._handle_websocket)

        # 5. Live HLS Streaming
        app.router.add_get("/live/stream.m3u8", self._handle_hls_playlist)
        app.router.add_get(r"/live/{segment:.*\.ts}", self._handle_hls_segment)

        # 6. Local Media Streaming (with HTTP 206 Range support)
        app.router.add_get("/media/stream", self._handle_media_stream)
        app.router.add_get("/media/stream.mp4", self._handle_media_stream)
        app.router.add_get("/media/subtitle.vtt", self._handle_subtitle)
        app.router.add_get("/media/subtitle.srt", self._handle_subtitle_srt)

        # 7. Status API
        app.router.add_get("/api/status", self._handle_api_status)

    async def _handle_options(self, request: web.Request):
        return web.Response(status=200, headers=CORS_HEADERS)

    async def _handle_discover_gif(self, request: web.Request):
        return web.Response(
            body=GIF_1X1,
            content_type="image/gif",
            headers={**CORS_HEADERS, "Cache-Control": "no-cache"},
        )

    async def _handle_beacon_gif(self, request: web.Request):
        client_ip = request.remote
        logger.info(f"Received TV beacon from {client_ip}")
        return web.Response(
            body=GIF_2X2,
            content_type="image/gif",
            headers={**CORS_HEADERS, "Cache-Control": "no-cache"},
        )

    async def _handle_receiver_connect(self, request: web.Request):
        client_ip = request.remote
        try:
            data = await request.json()
            receiver_info = data.get("receiver", {})
            label = receiver_info.get("label", "Smart TV")
            logger.info(f"TV connected via /connect: {label} ({client_ip})")
            app_state.set_tv_connected(True, client_ip, label)
        except Exception:
            app_state.set_tv_connected(True, client_ip, "Smart TV")

        return web.json_response({}, headers=CORS_HEADERS)

    async def _handle_request_connection(self, request: web.Request):
        client_ip = request.remote
        try:
            data = await request.json()
            receiver_info = data.get("receiver", {})
            label = receiver_info.get("label", "Smart TV")
            logger.info(f"TV requested connection: {label} ({client_ip})")
            app_state.set_tv_connected(True, client_ip, label)
        except Exception:
            app_state.set_tv_connected(True, client_ip, "Smart TV")

        self._tv_sent_initial_media = False
        # If streaming or casting is already active, enqueue loadMedia for the TV
        if app_state.current_mode == "screen_mirroring":
            self._enqueue_tv_command(self._build_wvc_load_stream_cmd())
            self._tv_sent_initial_media = True
        elif app_state.current_mode == "media_casting" and app_state.active_media_path:
            self._enqueue_tv_command(self._build_wvc_load_media_cmd())
            self._tv_sent_initial_media = True

        return web.json_response({"status": "ok"}, headers=CORS_HEADERS)

    async def _handle_long_poll(self, request: web.Request):
        client_ip = request.remote
        user_agent = request.headers.get("User-Agent", "Smart TV")
        if not app_state.tv_connected:
            logger.info(f"Smart TV LongPoll active from {client_ip} ({user_agent})")
        app_state.set_tv_connected(True, client_ip, user_agent)

        # If a stream or media is currently active and hasn't been sent to this TV session yet
        if not self._tv_sent_initial_media and not self._tv_command_queue:
            if app_state.current_mode == "screen_mirroring":
                self._tv_command_queue.append(self._build_wvc_load_stream_cmd())
                self._tv_sent_initial_media = True
            elif app_state.current_mode == "media_casting" and app_state.active_media_path:
                self._tv_command_queue.append(self._build_wvc_load_media_cmd())
                self._tv_sent_initial_media = True

        # Wait up to 25 seconds for a command, or return immediately if queued
        if not self._tv_command_queue:
            if self._tv_poll_event is None:
                self._tv_poll_event = asyncio.Event()
            self._tv_poll_event.clear()
            try:
                await asyncio.wait_for(self._tv_poll_event.wait(), timeout=25.0)
            except asyncio.TimeoutError:
                pass

        if self._tv_command_queue:
            cmd = self._tv_command_queue.pop(0)
            logger.info(f"Dispatching command to Smart TV ({client_ip}): {cmd.get('cmd')}")
            return web.json_response(cmd, headers=CORS_HEADERS)

        # Return empty JSON object on timeout so TV keeps polling without error
        return web.json_response({}, headers=CORS_HEADERS)

    async def _handle_tv_state(self, request: web.Request):
        try:
            data = await request.json()
            state = data.get("state")
            logger.info(f"TV Player State: {state}")
            if state == "idle" and app_state.current_mode == "media_casting":
                pass
        except Exception:
            pass
        return web.json_response({"status": "ok"}, headers=CORS_HEADERS)

    async def _handle_tv_position(self, request: web.Request):
        try:
            data = await request.json()
            # WVC TV sends position and duration in milliseconds!
            pos_ms = float(data.get("position", 0.0))
            dur_ms = float(data.get("duration", 0.0))
            app_state.update_media_progress(pos_ms / 1000.0, dur_ms / 1000.0)
        except Exception:
            pass
        return web.json_response({"status": "ok"}, headers=CORS_HEADERS)

    async def _handle_tv_media(self, request: web.Request):
        return web.json_response({"status": "ok"}, headers=CORS_HEADERS)

    async def _handle_tv_error(self, request: web.Request):
        try:
            data = await request.json()
            logger.warning(f"Smart TV reported playback error: {data}")
        except Exception:
            pass
        return web.json_response({"status": "ok"}, headers=CORS_HEADERS)

    async def _handle_tv_volume(self, request: web.Request):
        return web.json_response({"status": "ok"}, headers=CORS_HEADERS)

    async def _handle_tv_log(self, request: web.Request):
        try:
            data = await request.json()
            msg = data.get("message", "")
            if msg:
                logger.debug(f"[TV Log] {msg}")
        except Exception:
            pass
        return web.json_response({"status": "ok"}, headers=CORS_HEADERS)

    async def _handle_tv_disconnect(self, request: web.Request):
        logger.info("Smart TV disconnected.")
        app_state.set_tv_connected(False)
        self._tv_sent_initial_media = False
        return web.json_response({"status": "ok"}, headers=CORS_HEADERS)

    async def _handle_tv_device_info(self, request: web.Request):
        try:
            data = await request.json()
            brand = data.get("brand", "Smart TV")
            model = data.get(" buildVariant") or data.get("appVersion", "")
            logger.info(f"Smart TV Device Info: {brand} {model}")
            app_state.set_tv_connected(True, request.remote, f"{brand} {model}".strip())
        except Exception:
            pass
        return web.json_response({"status": "ok"}, headers=CORS_HEADERS)

    async def _handle_tv_ok(self, request: web.Request):
        return web.json_response({"status": "ok"}, headers=CORS_HEADERS)

    def _build_wvc_load_stream_cmd(self) -> Dict[str, Any]:
        base = self._get_base_url()
        return {
            "cmd": "loadMedia",
            "media": "video",
            "url": f"{base}/live/stream.m3u8?t={int(time.time())}",
            "mimeType": "application/vnd.apple.mpegurl",
            "position": 0,
            "poster": None,
            "subtitle": None,
            "corsOn": False,
            "corsServer": None,
            "headers": None,
            "hasNext": False,
            "hasPrevious": False,
        }

    def _build_wvc_load_media_cmd(self, subtitle_override: Optional[str] = None) -> Dict[str, Any]:
        base = self._get_base_url()
        media_path = app_state.active_media_path or ""
        content_type, _ = mimetypes.guess_type(media_path)
        content_type = content_type or "video/mp4"

        has_sub = bool(subtitle_override or app_state.active_subtitle_path)
        sub_url = f"{base}/media/subtitle.vtt?t={int(time.time())}" if has_sub else None

        return {
            "cmd": "loadMedia",
            "media": "video",
            "url": f"{base}/media/stream.mp4?t={int(time.time())}",
            "mimeType": content_type,
            "position": 0,
            "poster": None,
            "subtitle": sub_url,
            "corsOn": False,
            "corsServer": None,
            "headers": None,
            "hasNext": False,
            "hasPrevious": False,
        }

    def _translate_to_wvc_command(self, cmd: dict) -> Optional[Dict[str, Any]]:
        action = cmd.get("action")
        if action == "play_stream":
            self._tv_sent_initial_media = True
            return self._build_wvc_load_stream_cmd()
        elif action == "play_media":
            self._tv_sent_initial_media = True
            return self._build_wvc_load_media_cmd(cmd.get("subtitle"))
        elif action == "pause":
            return {"cmd": "pause"}
        elif action == "resume":
            return {"cmd": "play"}
        elif action == "stop":
            self._tv_sent_initial_media = False
            return {"cmd": "stop"}
        elif action == "seek":
            # WVC expects position in milliseconds
            pos_sec = float(cmd.get("time", 0.0))
            return {"cmd": "setPosition", "position": int(pos_sec * 1000)}
        elif action == "volume":
            level = float(cmd.get("level", 1.0))
            return {"cmd": "setVolume", "volume": level}
        return None

    def _enqueue_tv_command(self, wvc_cmd: Dict[str, Any]):
        if not self._loop:
            return

        def _put():
            # If a new loadMedia comes in, clear old pending commands
            if wvc_cmd.get("cmd") in ("loadMedia", "stop"):
                self._tv_command_queue.clear()
            self._tv_command_queue.append(wvc_cmd)
            if self._tv_poll_event:
                self._tv_poll_event.set()

        self._loop.call_soon_threadsafe(_put)

    async def _handle_index_redirect(self, request: web.Request):
        return web.HTTPFound("/web-receiver/index.html")

    async def _handle_serve_receiver_file(self, request: web.Request):
        filename = os.path.basename(request.path)
        filepath = os.path.join(self.web_root, filename)
        if not os.path.isfile(filepath):
            return web.HTTPNotFound(text="File not found")
        content_type, _ = mimetypes.guess_type(filepath)
        return web.FileResponse(filepath, headers={**CORS_HEADERS, "Content-Type": content_type or "application/octet-stream"})

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
                "url": "/media/stream.mp4",
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
                            logger.info("Browser reported media playback ended.")
                            app_state.set_mode("idle")
                        elif event == "error":
                            logger.warning(f"Browser reported error: {data.get('message')}")
                    except Exception as e:
                        logger.warning(f"Error handling WS message: {e}")
                elif msg.type == WSMsgType.ERROR:
                    logger.warning(f"WebSocket closed with exception: {ws.exception()}")
        finally:
            self._active_websockets.discard(ws)

        return ws

    async def _handle_hls_playlist(self, request: web.Request):
        m3u8_path = os.path.join(self.temp_hls_dir, "stream.m3u8")
        if not os.path.isfile(m3u8_path):
            return web.HTTPNotFound(text="Stream not ready yet")
        return web.FileResponse(
            m3u8_path,
            headers={
                **CORS_HEADERS,
                "Content-Type": "application/vnd.apple.mpegurl",
                "Cache-Control": "no-cache, no-store, must-revalidate",
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
                **CORS_HEADERS,
                "Content-Type": "video/mp2t",
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
            try:
                byte_range = range_header.replace("bytes=", "").split("-")
                start = int(byte_range[0])
                end = int(byte_range[1]) if len(byte_range) > 1 and byte_range[1] else file_size - 1
            except Exception:
                start = 0
                end = file_size - 1

            start = max(0, min(start, file_size - 1))
            end = max(start, min(end, file_size - 1))
            length = end - start + 1

            headers = {
                **CORS_HEADERS,
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(length),
                "Content-Type": content_type,
            }

            resp = web.StreamResponse(status=206, headers=headers)
            await resp.prepare(request)

            try:
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
            except (ConnectionResetError, asyncio.CancelledError):
                pass
            except Exception as e:
                logger.debug(f"Stream interrupted: {e}")
            return resp
        else:
            return web.FileResponse(
                media_path,
                headers={
                    **CORS_HEADERS,
                    "Accept-Ranges": "bytes",
                    "Content-Type": content_type,
                },
            )

    async def _handle_subtitle(self, request: web.Request):
        sub_path = app_state.active_subtitle_path
        if not sub_path or not os.path.isfile(sub_path):
            return web.HTTPNotFound(text="No subtitle available")
        return web.FileResponse(
            sub_path,
            headers={
                **CORS_HEADERS,
                "Content-Type": "text/vtt; charset=utf-8",
            },
        )

    async def _handle_subtitle_srt(self, request: web.Request):
        sub_path = app_state.active_subtitle_path
        if not sub_path or not os.path.isfile(sub_path):
            return web.HTTPNotFound(text="No subtitle available")
        return web.FileResponse(
            sub_path,
            headers={
                **CORS_HEADERS,
                "Content-Type": "text/plain; charset=utf-8",
            },
        )

    async def _handle_api_status(self, request: web.Request):
        return web.json_response(app_state.to_dict(), headers=CORS_HEADERS)

    def broadcast_command(self, cmd: dict):
        """Dispatches command to both Smart TV WVC Long-Poll queue and WebSocket clients."""
        # 1. Enqueue for Smart TV WVC App (/web-receiver-io/longPoll)
        wvc_cmd = self._translate_to_wvc_command(cmd)
        if wvc_cmd:
            self._enqueue_tv_command(wvc_cmd)

        # 2. Send to Browser WebSocket clients (/ws)
        if not self._loop or not self._active_websockets:
            return

        async def _send_all():
            for ws in list(self._active_websockets):
                if not ws.closed:
                    try:
                        await ws.send_json(cmd)
                    except Exception as e:
                        logger.warning(f"Error sending command to WS client: {e}")

        asyncio.run_coroutine_threadsafe(_send_all(), self._loop)

    def start(self):
        """Starts the aiohttp server in a dedicated background thread."""
        def run_server():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._tv_poll_event = asyncio.Event()

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
                if self._tv_poll_event:
                    self._tv_poll_event.set()
                await self._runner.cleanup()
                self._loop.stop()

            asyncio.run_coroutine_threadsafe(_cleanup(), self._loop)
            logger.info("Caster server stopped.")
