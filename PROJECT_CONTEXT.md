# 🧠 Web Video Caster - Proje Geliştirici ve Yapay Zeka Bağlamı (Project Context)

> Bu belge, projeyi devralan geliştiriciler ve yapay zeka kodlama asistanları (Cursor, VS Code, Copilot, Antigravity vb.) için projenin tüm mimarisini, tersine mühendislik protokol detaylarını, kararları ve yol haritasını özetler.

---

## 1. Proje Amacı ve Kapsamı
- **Hedef:** Windows 11 bilgisayarda çalışan, akıllı televizyondaki **Web Video Caster Receiver** (Android TV, Fire TV, LG webOS, Samsung Tizen) uygulamasına kendini uyumlu bir kaynak cihaz olarak tanıtarak:
  1. Bilgisayar ekranını sesiyle birlikte (Audio loopback) düşük gecikmeli olarak TV'ye yansıtan,
  2. Bilgisayardan seçilen video ve ses dosyalarını altyazısıyla (.srt/.vtt) TV'de takılmadan oynatan modern bir masaüstü uygulamasıdır.
- **Teknoloji Yığını:** Python 3.10+, PyQt6 (Windows 11 Fluent Dark UI), aiohttp (Asenkron HTTP & WebSocket Sunucusu), FFmpeg (Ekran & ses yakalama, HLS parçalama), Hls.js (TV içi gömülü web oynatıcı), PyInstaller (Tek tıkla EXE derleme).
- **GitHub Deposu:** [https://github.com/erennnys/wvc-screen-caster-win](https://github.com/erennnys/wvc-screen-caster-win) (Private)

---

## 2. Web Video Caster Protokolü (Tersine Mühendislik Bulguları)

Web Video Caster TV alıcısı (`com.instantbits.cast.receiver` ve `cast2tv.app`), sender (gönderici) ile şu standartlar üzerinden iletişim kurar:

### A. Base36 IP Eşleşme Algoritması (`src/core/base36.py`)
- TV veya PC yerel IP adresini doğrudan göstermek yerine kısa bir Base36 kodu üretir (örn. `9W`).
- Özel alt ağ ofsetleri:
  - `192.168.0.0` (başlangıç: `3232235520`)
  - `10.0.0.0` (başlangıç: `167772160`)
  - `172.16.0.0` (başlangıç: `2886729728`)
- Eğer yerel IP `192.168.1.100` ise, integer değerinden `192.168.0.0` çıkarılır ve kalan sayı (`356`) Base36 formatına çevrilerek `9W` kodu elde edilir.
- TV'ye `9W` yazıldığında TV, `http://192.168.1.100:30001/web-receiver/` adresine bağlanır.

### B. HTTP ve Keşif Uç Noktaları (`src/core/server.py`)
- **Varsayılan Port:** `30001` (doluysa `30002` veya `30003`).
- `GET /web-receiver/discover.gif`: 1x1 şeffaf GIF döner (TV'nin cihazı canlı olarak tanıması için).
- `GET /web-receiver-io/cast2tv.gif`: 2x2 piksel GIF döner. WVC kaynak kodunda `if (image.naturalWidth == 2 && image.naturalHeight == 2) connectToSender()` tetiklenir, TV otomatik olarak bağlanır.
- `POST /web-receiver-io/connect`: TV'nin bağlandığını bildiren JSON bildirimi (`{ "receiver": { ... } }`).
- `GET /web-receiver/index.html`: TV'nin açtığı tam ekran HTML5 oynatıcı arayüzü.

### C. Çift Yönlü WebSocket Protokolü (`/ws`)
Masaüstü uygulaması ve TV oynatıcısı arasındaki tüm kontroller WebSocket üzerinden gerçek zamanlı akar:
- **PC -> TV Emirleri:**
  - `play_stream`: Canlı ekran HLS akışını başlatır (`/live/stream.m3u8`).
  - `play_media`: Yerel video dosyasını başlatır (`/media/stream`, altyazı: `/media/subtitle.vtt`).
  - `pause`, `resume`: Duraklatma / devam ettirme.
  - `seek`: Belirli bir saniyeye sarma (`time: float`).
  - `volume`: Ses seviyesi ayarlama (`level: 0.0 - 1.0`).
  - `stop`: Oynatmayı durdurup karşılama ekranına dönme.
- **TV -> PC Geri Bildirimleri:**
  - `receiver_ready`: TV ekran çözünürlüğü ve User-Agent bilgisi.
  - `timeupdate`: Güncel saniye ve toplam süre (`currentTime`, `duration`).
  - `play`, `pause`, `ended`, `error`: Oynatıcı durum güncellemeleri.

---

## 3. Kod Tabanı Mimarisi (Codebase Map)

```
wvc-screen-caster-win/
├── main.py                     # Başlangıç noktası: DPI ayarları, sunucu ve GUI başlatma
├── requirements.txt            # Bağımlılıklar (PyQt6, aiohttp, pyinstaller)
├── build_exe.bat               # Windows için tek tıkla EXE derleme betiği
├── README.md                   # Kullanıcı dokümantasyonu
├── PROJECT_CONTEXT.md          # Bu bağlam belgesi
├── .github_ci/build.yml        # Windows EXE derleyen GitHub CI iş akışı
│
├── src/
│   ├── core/
│   │   ├── base36.py           # Base36 IP/Kod dönüştürücü ve varyasyon analizcisi
│   │   ├── server.py           # aiohttp HTTP & WebSocket sunucusu (Range 206 streaming)
│   │   ├── streamer.py         # FFmpeg ekran (gdigrab) & ses yakalama, HLS parçalayıcı
│   │   ├── media_caster.py     # Yerel medya yöneticisi, FFprobe metadata, SRT->VTT dönüştürücü
│   │   ├── discovery.py        # Ağ tarayıcısı ve TV IP çözümleyici
│   │   └── state.py            # İş parçacığı güvenli (thread-safe) uygulama durum yöneticisi
│   │
│   ├── receiver_web/           # TV'de çalışan web uygulaması (tamamen çevrimdışı çalışır)
│   │   ├── index.html          # TV arayüzü ve video etiketi
│   │   ├── player.js           # WebSocket komut dinleyicisi ve oynatıcı yöneticisi
│   │   ├── style.css           # TV dostu karanlık stil, HUD paneli ve altyazı tasarımı
│   │   └── hls.min.js          # Gömülü Hls.js kütüphanesi
│   │
│   ├── ui/
│   │   ├── main_window.py      # PyQt6 Ana Penceresi ve Sekmeler
│   │   ├── connection_widget.py# Üst bağlantı rozeti, kod gösterimi ve manuel TV bağlantısı
│   │   ├── screen_tab.py       # Ekran yansıtma (Çözünürlük, FPS, Ses, Encoder seçimi)
│   │   ├── media_tab.py        # Medya dosyası seçimi, scrubber seek bar, ses düzeyi
│   │   └── styles.py           # Windows 11 Fluent Dark Theme QSS stilleri
│   │
│   └── utils/
│       ├── ffmpeg_finder.py    # FFmpeg/FFprobe tespiti ve donanım hızlandırma kontrolü
│       ├── network.py          # Birincil yerel IP tespiti ve port kontrolü
│       └── logger.py           # GUI'ye bağlı canlı log yakalayıcı
```

---

## 4. Windows 11 Üzerinde Çalıştırma ve Derleme

### Geliştirici Modunda Çalıştırma:
```cmd
cd wvc-screen-caster-win
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Taşınabilir Tek `.exe` Olarak Derleme:
```cmd
build_exe.bat
```
Çıktı: `dist\WVC_Caster\WVC_Caster.exe`

---

## 5. Sıradaki Geliştirmeler ve Yol Haritası (Roadmap)

Projeye devam ederken yapılabilecek geliştirmeler:
1. **Çoklu Monitör Desteği:**
   - Birden fazla monitör olan sistemlerde `screen_tab.py` üzerinden yansıtılacak ekranın seçilebilmesi (`-offset_x`, `-offset_y` parametreleriyle FFmpeg entegrasyonu).
2. **Doğrudan DirectX Desktop Duplication (DXGI):**
   - FFmpeg 6+ ile gelen `-f lavfi -i ddagrab` desteği ile CPU kullanımı daha da düşürülebilir.
3. **Ses Giriş Aygıtı Seçici:**
   - `get_dshow_audio_devices()` fonksiyonu `screen_tab.py` içine bir açılır menü (combobox) olarak bağlanabilir.
4. **Sistem Tepsisi (System Tray):**
   - Pencere kapatıldığında arka planda çalışmaya devam etmesi için `QSystemTrayIcon` desteği.
