/**
 * WVC TV Web Receiver Player Controller
 * Handles WebSocket communication with the Windows Caster app,
 * controls HLS live streaming and native media file playback with subtitles.
 */

(function () {
    const video = document.getElementById('video-player');
    const splashScreen = document.getElementById('splash-screen');
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    const instructionsText = document.getElementById('instructions-text');
    const overlayHud = document.getElementById('overlay-hud');
    const hudTitle = document.getElementById('hud-title');
    const hudSub = document.getElementById('hud-sub');
    const hudTime = document.getElementById('hud-time');

    let ws = null;
    let hls = null;
    let hudTimeout = null;
    let currentMode = 'idle'; // 'idle', 'live', 'media'

    // Format seconds to MM:SS or HH:MM:SS
    function formatTime(seconds) {
        if (!seconds || isNaN(seconds) || !isFinite(seconds)) return "00:00";
        const s = Math.floor(seconds);
        const hrs = Math.floor(s / 3600);
        const mins = Math.floor((s % 3600) / 60);
        const secs = s % 60;
        if (hrs > 0) {
            return `${hrs}:${mins < 10 ? '0' : ''}${mins}:${secs < 10 ? '0' : ''}${secs}`;
        }
        return `${mins < 10 ? '0' : ''}${mins}:${secs < 10 ? '0' : ''}${secs}`;
    }

    function showHud(title, sub, duration = 3500) {
        if (title) hudTitle.textContent = title;
        if (sub) hudSub.textContent = sub;
        overlayHud.classList.add('visible');
        if (hudTimeout) clearTimeout(hudTimeout);
        if (duration > 0) {
            hudTimeout = setTimeout(() => {
                overlayHud.classList.remove('visible');
            }, duration);
        }
    }

    function hideHud() {
        overlayHud.classList.remove('visible');
    }

    function setStatus(state, message) {
        statusDot.className = 'status-dot ' + state;
        statusText.textContent = message;
    }

    function sendEvent(event, data = {}) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            const payload = { event, ...data, timestamp: Date.now() };
            ws.send(JSON.stringify(payload));
        }
    }

    // Connect WebSocket to Windows Host
    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        setStatus('connecting', 'Bilgisayara bağlanıyor...');

        ws = new WebSocket(wsUrl);

        ws.onopen = function () {
            console.log("[WVC Receiver] WebSocket connected to", wsUrl);
            setStatus('connected', 'Bilgisayar Bağlandı');
            instructionsText.innerHTML = "Bağlantı kuruldu! Bilgisayarınızdan <b>Ekran Yansıtma</b> veya <b>Medya Yayını</b> başlatabilirsiniz.";
            sendEvent('receiver_ready', {
                userAgent: navigator.userAgent,
                screenWidth: window.innerWidth,
                screenHeight: window.innerHeight
            });
        };

        ws.onmessage = function (event) {
            try {
                const msg = JSON.parse(event.data);
                handleCommand(msg);
            } catch (err) {
                console.error("[WVC Receiver] Invalid message JSON:", err, event.data);
            }
        };

        ws.onclose = function () {
            console.log("[WVC Receiver] WebSocket disconnected. Reconnecting in 3s...");
            setStatus('disconnected', 'Bağlantı Kesildi - Yeniden deneniyor...');
            setTimeout(connectWebSocket, 3000);
        };

        ws.onerror = function (err) {
            console.error("[WVC Receiver] WebSocket error:", err);
            ws.close();
        };
    }

    // Stop current playback and clean up resources
    function stopPlayback() {
        if (hls) {
            hls.destroy();
            hls = null;
        }
        video.pause();
        video.removeAttribute('src');
        video.load();

        // Remove any text tracks
        while (video.firstChild) {
            video.removeChild(video.firstChild);
        }

        video.classList.remove('active');
        splashScreen.style.display = 'flex';
        currentMode = 'idle';
        hideHud();
    }

    // Command Dispatcher from Desktop App
    function handleCommand(msg) {
        console.log("[WVC Receiver] Command received:", msg);

        switch (msg.action) {
            case 'play_stream':
                startLiveStream(msg.url || '/live/stream.m3u8', msg.title || 'Ekran Yansıtma');
                break;

            case 'play_media':
                startMediaFile(msg.url || '/media/stream', msg.title || 'Medya Yayını', msg.subtitle);
                break;

            case 'pause':
                video.pause();
                showHud(null, "Duraklatıldı", 2500);
                break;

            case 'resume':
                video.play().catch(e => console.warn("Play blocked:", e));
                showHud(null, "Oynatılıyor", 2500);
                break;

            case 'seek':
                if (typeof msg.time === 'number') {
                    video.currentTime = msg.time;
                    showHud(null, `Konum: ${formatTime(msg.time)}`, 2500);
                }
                break;

            case 'volume':
                if (typeof msg.level === 'number') {
                    video.volume = Math.max(0, Math.min(1, msg.level));
                    showHud(null, `Ses: ${Math.round(video.volume * 100)}%`, 2000);
                }
                break;

            case 'stop':
                stopPlayback();
                sendEvent('stopped');
                break;

            default:
                console.warn("[WVC Receiver] Unknown action:", msg.action);
        }
    }

    // Play Live HLS Stream (Screen Mirroring)
    function startLiveStream(streamUrl, title) {
        stopPlayback();
        currentMode = 'live';

        splashScreen.style.display = 'none';
        video.classList.add('active');
        showHud(title, "Canlı Ekran Akışı Başlatılıyor...", 4000);

        if (Hls.isSupported()) {
            hls = new Hls({
                enableWorker: true,
                lowLatencyMode: true,
                liveSyncDurationCount: 1,
                liveMaxLatencyDurationCount: 3,
                maxBufferLength: 4,
                backBufferLength: 0
            });

            hls.loadSource(streamUrl);
            hls.attachMedia(video);

            hls.on(Hls.Events.MANIFEST_PARSED, function () {
                console.log("[WVC Receiver] HLS manifest parsed, playing stream...");
                video.play().catch(err => {
                    console.warn("Auto-play prevented, waiting for user click/event:", err);
                });
                showHud(title, "Canlı Yayın", 3000);
            });

            hls.on(Hls.Events.ERROR, function (event, data) {
                console.warn("[WVC Receiver] HLS Error:", data);
                if (data.fatal) {
                    switch (data.type) {
                        case Hls.ErrorTypes.NETWORK_ERROR:
                            console.log("HLS network error, recovering...");
                            hls.startLoad();
                            break;
                        case Hls.ErrorTypes.MEDIA_ERROR:
                            console.log("HLS media error, recovering...");
                            hls.recoverMediaError();
                            break;
                        default:
                            console.error("HLS fatal error, destroying...");
                            stopPlayback();
                            break;
                    }
                }
            });
        } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
            // Native Safari / Apple TV HLS support
            video.src = streamUrl;
            video.play().catch(e => console.warn(e));
        } else {
            console.error("HLS not supported on this browser/receiver");
            sendEvent('error', { message: 'HLS formatı desteklenmiyor' });
        }
    }

    // Play Direct Media File (Local MP4/MKV stream with optional subtitles)
    function startMediaFile(mediaUrl, title, subtitleUrl) {
        stopPlayback();
        currentMode = 'media';

        splashScreen.style.display = 'none';
        video.classList.add('active');
        showHud(title, "Medya Yükleniyor...", 3000);

        // Add subtitle track if provided
        if (subtitleUrl) {
            const track = document.createElement('track');
            track.kind = 'subtitles';
            track.label = 'Altyazı';
            track.srclang = 'tr';
            track.src = subtitleUrl;
            track.default = true;
            video.appendChild(track);
        }

        // Smart TVs (TiVo/Vestel/webOS) require absolute URL with timestamp to prevent aggressive cache
        const finalUrl = (mediaUrl.startsWith('http') ? mediaUrl : window.location.origin + mediaUrl) + '?t=' + Date.now();
        video.src = finalUrl;
        video.load();
        
        // Ensure muted playback start fallback if autoplay policy blocks it on TV
        const playPromise = video.play();
        if (playPromise !== undefined) {
            playPromise.then(() => {
                showHud(title, "Oynatılıyor", 3000);
            }).catch(err => {
                console.warn("Media play error, retrying muted:", err);
                video.muted = true;
                video.play().then(() => {
                    video.muted = false;
                    showHud(title, "Oynatılıyor", 3000);
                }).catch(e2 => {
                    console.error("Fatal playback failure:", e2);
                    sendEvent('error', { message: 'Medya oynatılamadı: ' + e2.message });
                });
            });
        }
    }

    // Video Element Events Forwarding to Desktop App
    video.addEventListener('timeupdate', function () {
        if (currentMode === 'media') {
            hudTime.textContent = `${formatTime(video.currentTime)} / ${formatTime(video.duration)}`;
            sendEvent('timeupdate', {
                currentTime: video.currentTime,
                duration: video.duration || 0
            });
        }
    });

    video.addEventListener('play', function () {
        sendEvent('play');
    });

    video.addEventListener('pause', function () {
        sendEvent('pause');
    });

    video.addEventListener('ended', function () {
        sendEvent('ended');
        stopPlayback();
    });

    video.addEventListener('error', function (e) {
        console.error("[WVC Receiver] Video error event:", video.error);
        sendEvent('error', {
            code: video.error ? video.error.code : 0,
            message: video.error ? video.error.message : 'Bilinmeyen video hatası'
        });
    });

    // Start WebSocket Connection
    connectWebSocket();
})();
