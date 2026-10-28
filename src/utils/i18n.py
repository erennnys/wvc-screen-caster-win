"""
Bilingual (Turkish & English) Internationalization (i18n) Manager.
"""

from typing import Callable, List

TRANSLATIONS = {
    "tr": {
        "app_title": "WVC Studio — Ekran ve Medya Yansıtıcı",
        "app_subtitle": "Web Video Caster Akıllı TV Yansıtma Merkezi",
        "status_waiting": "TV Bağlantısı Bekleniyor",
        "status_connected": "TV Bağlandı: {ip}",
        "pairing_code_label": "EŞLEŞME KODU",
        "pairing_hint": "Televizyonunuzdaki Web Video Caster uygulamasında <b>Kod Gir (Enter Code)</b> bölümüne <b>{code}</b> yazın veya tarayıcıdan <b>http://{ip}:{port}</b> adresini açın.",
        "manual_ip_label": "Manuel Bağlantı:",
        "manual_ip_placeholder": "TV Kodu veya IP (örn. 192.168.1.50)",
        "btn_connect": "Bağlan",
        "btn_checking": "Kontrol Ediliyor...",
        "btn_scan": "Ağı Tara",
        "btn_scanning": "Taranıyor...",
        "tab_screen": "🖥️  Ekran Yansıtma",
        "tab_media": "🎬  Medya Oynatıcı",
        # Screen Tab
        "screen_card_title": "Görüntü ve Ses Yapılandırması",
        "screen_card_desc": "Masaüstü ekranınızı düşük gecikmeli canlı HLS akışı olarak televizyonunuza aktarır.",
        "lbl_resolution": "Çözünürlük",
        "res_1080p": "1920x1080 (Full HD - Önerilen)",
        "res_720p": "1280x720 (HD - En Düşük Gecikme)",
        "res_1440p": "2560x1440 (2K QHD)",
        "res_4k": "3840x2160 (4K Ultra HD)",
        "lbl_fps": "Kare Hızı (FPS)",
        "fps_30": "30 FPS (Akıcı ve Kararlı)",
        "fps_60": "60 FPS (Yüksek Akıcılık)",
        "fps_24": "24 FPS (Sinematik)",
        "lbl_encoder": "Video Kodlayıcı",
        "lbl_audio": "Bilgisayar Sesini Televizyona Aktar (Stereo Mix / Loopback)",
        "stream_status_title": "Yayın Durumu",
        "stream_status_idle": "Hazır — Yayın Bekleniyor",
        "stream_status_live": "CANLI YAYINDA",
        "stream_duration": "Süre: {time}",
        "btn_start_screen": "Ekran Yansıtmayı Başlat",
        "btn_stop_screen": "Ekran Yansıtmayı Durdur",
        # Media Tab
        "media_card_title": "Yerel Medya Seçimi",
        "media_card_desc": "Bilgisayarınızdaki film, dizi ve videoları kayıpsız kalitede doğrudan TV oynatıcısında açar.",
        "btn_select_video": "Video veya Ses Dosyası Seç",
        "btn_select_sub": "Altyazı Ekle (.srt / .vtt)",
        "no_file_selected": "Henüz bir medya dosyası seçilmedi",
        "selected_file": "Dosya: {name}",
        "meta_template": "Süre: {dur}   •   Çözünürlük: {res}   •   Video: {vcodec}   •   Ses: {acodec}{sub}",
        "meta_audio_only": "Ses Dosyası",
        "meta_sub_ready": "   •   Altyazı Hazır ✓",
        "player_card_title": "Uzaktan Oynatıcı Kontrolleri",
        "btn_play": "Oynat",
        "btn_pause": "Duraklat",
        "btn_stop": "Durdur",
        "lbl_volume": "Ses",
        "btn_cast_media": "Televizyonda Oynat",
        # Dialogs & Status
        "sb_server_port": "Sunucu: {ip}:{port}",
        "sb_ready": "Sistem Hazır",
        "dlg_warn_title": "Uyarı",
        "dlg_enter_code": "Lütfen TV ekranında görünen kodu veya IP adresini girin.",
        "dlg_success_title": "Bağlantı Başarılı",
        "dlg_tv_found": "Televizyon bulundu ({ip}) ve yayına hazır!",
        "dlg_not_found_title": "Cihaz Bulunamadı",
        "dlg_not_found_msg": "'{val}' adresinde aktif bir TV bulunamadı.\nEn hızlı bağlantı için TV uygulamasında '{code}' kodunu girin.",
        "dlg_scan_done_title": "Ağ Taraması",
        "dlg_scan_found": "Ağda uyumlu televizyon bulundu: {ip}",
        "dlg_scan_none": "Otomatik taramada TV yanıt vermedi.\nLütfen TV'deki uygulamada '{code}' eşleşme kodunu girin.",
    },
    "en": {
        "app_title": "WVC Studio — Screen & Media Caster",
        "app_subtitle": "Web Video Caster Smart TV Streaming Hub",
        "status_waiting": "Waiting for TV Connection",
        "status_connected": "TV Connected: {ip}",
        "pairing_code_label": "PAIRING CODE",
        "pairing_hint": "Open <b>Web Video Caster</b> on your TV, select <b>Enter Code</b> and type <b>{code}</b>, or visit <b>http://{ip}:{port}</b> on your TV browser.",
        "manual_ip_label": "Manual Connect:",
        "manual_ip_placeholder": "TV Code or IP (e.g. 192.168.1.50)",
        "btn_connect": "Connect",
        "btn_checking": "Checking...",
        "btn_scan": "Scan Network",
        "btn_scanning": "Scanning...",
        "tab_screen": "🖥️  Screen Mirroring",
        "tab_media": "🎬  Media Player",
        # Screen Tab
        "screen_card_title": "Display & Audio Configuration",
        "screen_card_desc": "Stream your desktop screen live to your Smart TV with ultra-low latency HLS.",
        "lbl_resolution": "Resolution",
        "res_1080p": "1920x1080 (Full HD - Recommended)",
        "res_720p": "1280x720 (HD - Lowest Latency)",
        "res_1440p": "2560x1440 (2K QHD)",
        "res_4k": "3840x2160 (4K Ultra HD)",
        "lbl_fps": "Frame Rate (FPS)",
        "fps_30": "30 FPS (Smooth & Stable)",
        "fps_60": "60 FPS (High Frame Rate)",
        "fps_24": "24 FPS (Cinematic)",
        "lbl_encoder": "Video Encoder",
        "lbl_audio": "Stream System Audio to TV (Stereo Mix / Loopback)",
        "stream_status_title": "Stream Status",
        "stream_status_idle": "Ready — Idle",
        "stream_status_live": "LIVE STREAMING",
        "stream_duration": "Duration: {time}",
        "btn_start_screen": "Start Screen Mirroring",
        "btn_stop_screen": "Stop Screen Mirroring",
        # Media Tab
        "media_card_title": "Local Media Selection",
        "media_card_desc": "Play local movies, shows, and videos directly on your TV's native media player.",
        "btn_select_video": "Choose Video or Audio File",
        "btn_select_sub": "Add Subtitle (.srt / .vtt)",
        "no_file_selected": "No media file selected yet",
        "selected_file": "File: {name}",
        "meta_template": "Duration: {dur}   •   Resolution: {res}   •   Video: {vcodec}   •   Audio: {acodec}{sub}",
        "meta_audio_only": "Audio Track",
        "meta_sub_ready": "   •   Subtitle Ready ✓",
        "player_card_title": "Remote Playback Controls",
        "btn_play": "Play",
        "btn_pause": "Pause",
        "btn_stop": "Stop",
        "lbl_volume": "Volume",
        "btn_cast_media": "Play on TV",
        # Dialogs & Status
        "sb_server_port": "Server: {ip}:{port}",
        "sb_ready": "System Ready",
        "dlg_warn_title": "Warning",
        "dlg_enter_code": "Please enter the code shown on your TV or its IP address.",
        "dlg_success_title": "Connected",
        "dlg_tv_found": "Smart TV found ({ip}) and ready for casting!",
        "dlg_not_found_title": "Device Not Found",
        "dlg_not_found_msg": "Could not reach a TV at '{val}'.\nFor instant pairing, enter code '{code}' on your TV app.",
        "dlg_scan_done_title": "Network Scan",
        "dlg_scan_found": "Compatible Smart TV found on network: {ip}",
        "dlg_scan_none": "No TV responded to automatic scan.\nPlease enter pairing code '{code}' inside your TV app.",
    },
}


class I18nManager:
    def __init__(self, default_lang: str = "tr"):
        self._lang = default_lang if default_lang in TRANSLATIONS else "tr"
        self._listeners: List[Callable[[str], None]] = []

    @property
    def lang(self) -> str:
        return self._lang

    def set_lang(self, lang: str):
        if lang in TRANSLATIONS and lang != self._lang:
            self._lang = lang
            for cb in list(self._listeners):
                try:
                    cb(self._lang)
                except Exception:
                    pass

    def t(self, key: str, **kwargs) -> str:
        text = TRANSLATIONS.get(self._lang, TRANSLATIONS["tr"]).get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text

    def on_change(self, callback: Callable[[str], None]):
        if callback not in self._listeners:
            self._listeners.append(callback)


i18n = I18nManager("tr")
