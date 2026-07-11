# Flipper WiFi Devboard - Hotspot Manager

Aplikasi Web Control Panel berbasis Flask dengan visual bertema **Flipper Zero** untuk mengelola Hotspot Wi-Fi di Raspberry Pi secara interaktif.

## Fitur Utama

- **Desain Khas Flipper Zero**: Menggunakan warna oranye ikonik, tipografi monospace, LCD monokrom, dan maskot lumba-lumba ASCII.
- **Ekspresi Maskot Dinamis**: Maskot lumba-lumba berubah reaksi secara real-time berdasarkan status hotspot (Idle `zzz`, Memproses `Working...`, Aktif `AP IS UP!`).
- **Pendeteksian Interface Dinamis**: Memindai interface nirkabel yang tersedia di Raspberry Pi secara otomatis (`wlan0`, `wlan1`, dll.).
- **Deteksi IP Otentik**: Menampilkan alamat IPv4 yang sebenarnya dari interface yang aktif.
- **Konsol Output Log**: Menampilkan log perintah sistem (`nmcli`) secara real-time di bawah dashboard.

---

## Persyaratan Sistem

- Raspberry Pi dengan **NetworkManager** terpasang (bawaan pada Raspberry Pi OS Bookworm terbaru).
- Python 3.x.

---

## Panduan Penggunaan (Instalasi & Menjalankan)

### 1. Persiapan Folder & Virtual Environment
Pindahkan seluruh berkas ke direktori proyek di Raspberry Pi Anda. Buat dan aktifkan virtual environment:

**Di Linux (Raspberry Pi):**
```bash
# Membuat Virtual Environment
python -m venv .venv

# Mengaktifkan Virtual Environment
source .venv/bin/activate

# Memasang dependensi
pip install -r requirements.txt
```

**Di Windows (Untuk Simulasi/Development):**
```powershell
# Membuat Virtual Environment
python -m venv .venv

# Mengaktifkan Virtual Environment
.venv\Scripts\Activate.ps1

# Memasang dependensi
pip install -r requirements.txt
```

### 2. Menjalankan Server
Jalankan aplikasi dengan hak akses administrator (`sudo`) agar Python memiliki izin untuk mengonfigurasi perangkat jaringan (`nmcli`):

```bash
sudo .venv/bin/python hotspot_web.py
```

### 3. Akses Dashboard
Buka browser pada perangkat lain (seperti HP atau Laptop) yang terhubung ke jaringan lokal yang sama dengan Raspberry Pi, lalu akses link:
```text
http://<IP_RASPBERRY_PI>:5002
```
*(Ganti `<IP_RASPBERRY_PI>` dengan alamat IP internal Raspberry Pi Anda).*
