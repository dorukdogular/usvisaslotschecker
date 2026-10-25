# İstanbul ABD Konsolosluğu Randevu Botu

Türkiye / İstanbul için uyarlanmış ABD vize randevu takip botu. Müsait slot görünce **Telegram** (ana) ve isteğe bağlı **e-posta** ile anında bildirir.

> **Kaynak ve uyarlama**  
> Bu proje, [Abhishek Kataria](https://github.com/Abhishekkataria16)’nın Hindistan (India) konsolosluk / VAC slotlarını izleyen açık kaynak botundan forklanmıştır:  
> **[Abhishekkataria16/USVisaSlotsChecker](https://github.com/Abhishekkataria16/USVisaSlotsChecker)**  
> **Doruk Doğular** tarafından Türkiye’ye (İstanbul ABD Konsolosluğu) uyarlanmış; hibrit mimari, Cloudflare-dostu istemci, proxy, rate-limit koruması ve Telegram bildirimi eklenmiştir.

---

## İçindekiler

1. [Ne yapar?](#ne-yapar)
2. [Önkoşullar](#önkoşullar)
3. [checkvisaslots API anahtarı](#1-checkvisaslots-api-anahtarı)
4. [Telegram kurulumu](#2-telegram-kurulumu)
5. [E-posta (opsiyonel)](#3-e-posta-opsiyonel)
6. [Yerel / Docker kurulum](#4-yerel--docker-kurulum)
7. [Ücretsiz host nerede?](#5-ücretsiz-host-nerede)
8. [Oracle Cloud adım adım](#6-oracle-cloud-always-free--önerilen)
9. [Ortam değişkenleri](#7-ortam-değişkenleri)
10. [Çalışma mantığı](#8-çalışma-mantığı)
11. [Testler ve sorun giderme](#9-testler-ve-sorun-giderme)
12. [Uyarılar](#10-uyarılar)
13. [Lisans](#lisans)

---

## Ne yapar?

| Özellik | Açıklama |
|--------|----------|
| Kaynak (Phase 1) | [checkvisaslots.com](https://checkvisaslots.com) API — İstanbul slotları |
| Kaynak (Phase 2) | Resmi `ustraveldocs.com` için **stub** (varsayılan kapalı; randevu almaz) |
| Bildirim | Telegram + isteğe bağlı e-posta / Pushover |
| Koruma | `curl_cffi` (Chrome TLS), Tinyproxy, jitter’lı aralık, 403/429 backoff |
| Filtre | `VISA_LOCATIONS=ISTANBUL`, `VISA_CATEGORIES=B1/B2` (ayarlanabilir) |
| Spam engeli | Aynı slot ~6 saat tekrar bildirilmez (dedupe) |

Bot **yalnızca bildirir**; randevuyu sen resmi siteden alırsın: [ustraveldocs.com/tr](https://www.ustraveldocs.com/tr)

---

## Önkoşullar

- Docker + Docker Compose **veya** Python 3.10+
- checkvisaslots hesabı (API key)
- Telegram bot token + chat id
- 7/24 açık kalacak bir makine / VPS (ücretsiz seçenekler aşağıda)

---

## 1) checkvisaslots API anahtarı

1. [https://checkvisaslots.com](https://checkvisaslots.com) adresine git → **Register** ile ücretsiz hesap aç.
2. Giriş yap → dashboard / ayarlar bölümünden **API Key** (Access Code) değerini kopyala.
3. Chrome eklentisini kullanıyorsan aynı anahtar genelde eklenti ayarlarında da görünür.
4. `.env` dosyasına yaz:

```env
API_KEY=buraya_yapistir
```

> Ücretsiz planda günlük sorgu kotası sınırlı olabilir. Bot, API’den gelen `remaining` değeri düşünce kontrol aralığını otomatik uzatır.

İlk çalıştırmada loglarda API’nin döndürdüğü gerçek `visa_location` isimlerini göreceksin. İstanbul için genelde `ISTANBUL` yeterlidir; farklıysa `.env` içinde güncelle.

---

## 2) Telegram kurulumu

### Bot oluşturma

1. Telegram’da [@BotFather](https://t.me/BotFather) aç.
2. `/newbot` yaz → bot adı ve kullanıcı adı ver (kullanıcı adı `...bot` ile bitmeli).
3. BotFather’ın verdiği token’ı kopyala:

```env
TELEGRAM_BOT_TOKEN=123456789:AAH...
```

### Chat ID alma

1. Oluşturduğun bota Telegram’dan `/start` yaz.
2. Tarayıcıda şunu aç (token’ı kendi token’ınla değiştir):

```
https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates
```

3. JSON içindeki `"chat":{"id": **********}` değerini al:

```env
TELEGRAM_CHAT_ID=123456789
```

**Grup** kullanacaksan: botu gruba ekle, grupta bir mesaj yaz, yine `getUpdates` ile bak. Grup id’leri çoğu zaman `-100...` ile başlar.

### Hızlı test

```bash
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d chat_id="${TELEGRAM_CHAT_ID}" \
  -d text="Visa bot test — İstanbul"
```

Mesaj gelirse Telegram tarafı tamam.

---

## 3) E-posta (opsiyonel)

Telegram yeterlidir. Yine de e-posta istersen:

```env
SENDER_EMAIL=senin@gmail.com
SENDER_PASSWORD=uygulama_sifresi
RECEIVER_EMAIL=alici@email.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
```

Gmail için normal şifre değil, [Google App Password](https://myaccount.google.com/apppasswords) kullan (2FA açık olmalı).

---

## 4) Yerel / Docker kurulum

### Hızlı yol (Docker — önerilen)

```bash
git clone https://github.com/dorukdogular/usvisaslotschecker.git
cd usvisaslotschecker

cp .env.example .env
# .env içini düzenle: API_KEY, TELEGRAM_*, isteğe bağlı SMTP

docker compose up -d --build
docker compose logs -f visa-checker
```

Servisler:

- `proxy` — Tinyproxy (`http://proxy:8888`)
- `visa-checker` — jitter’lı kontrol döngüsü
- `flaresolverr` — opsiyonel; `docker compose --profile cf up -d` ile açılır

### Proxy smoke test

```bash
docker compose up -d proxy
docker compose run --rm -e PROXY_URL=http://proxy:8888 visa-checker \
  python -m src proxy-test
```

Docker yoksa lokal basit proxy:

```bash
python3 scripts/simple_proxy.py --port 8888 &
PROXY_URL=http://127.0.0.1:8888 python3 -m src proxy-test
```

### Docker’suz Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# PROXY_URL=http://127.0.0.1:8888  # isteğe bağlı

# Tek seferlik kontrol
RUN_MODE=once python3 -m src once

# Sürekli döngü (production)
RUN_MODE=loop python3 -m src loop
```

Dry-run (bildirim göndermeden):

```bash
DRY_RUN=true NOTIFY=false RUN_MODE=once python3 -m src once
```

---

## 5) Ücretsiz host nerede?

Botun **sürekli açık** kalması gerekir (yaklaşık her 5 dakikada bir + jitter). “Uyuyan” free PaaS’ler slot kaçırır.

| Seçenek | Ücretsiz mi? | 7/24 uygun mu? | Not |
|---------|--------------|----------------|-----|
| **Oracle Cloud Always Free (VM)** | Evet | Evet | **En iyi seçenek** — Docker Compose kur |
| Ev PC / Raspberry Pi | Evet | Bilgisayar açıksa | En basit |
| GitHub Actions (scheduled) | Evet (dakika kotası) | Kısmen | Secret’lara `.env`; loop kadar sık değil |
| Railway / Render free | Sınırlı | Zayıf | Uyku / süre bitince durur |
| Fly.io free allowance | Sınırlı | Değişken | Kota bitince durabilir |

**Tavsiye:** Oracle Always Free Ubuntu VM + bu repodaki `docker compose`.

---

## 6) Oracle Cloud Always Free — önerilen

### A) Hesap ve VM

1. [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/) hesabı aç.
2. **Compute → Instances → Create**  
   - Image: **Ubuntu 22.04**  
   - Shape: Always Free uyumlu (ör. `VM.Standard.E2.1.Micro` veya ARM Ampere free)
3. SSH public key ekle, instance’ı oluştur.
4. **Networking:** Ingress’te SSH (22) açık olsun. Bot dışarıdan port yayınlamak zorunda değil; sadece çıkış trafiği yeter.

### B) Sunucuya bağlan ve kur

```bash
ssh ubuntu@<VM_PUBLIC_IP>

sudo apt update
sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker ubuntu
# çıkış yapıp tekrar SSH ile gir (docker grubu için)

git clone https://github.com/dorukdogular/usvisaslotschecker.git
cd usvisaslotschecker
cp .env.example .env
nano .env   # API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID doldur

sudo docker compose up -d --build
sudo docker compose logs -f visa-checker
```

### C) Kalıcı çalıştığını doğrula

```bash
sudo docker compose ps
# visa-checker ve proxy "Up" olmalı

# Son başarılı kontrol zamanı
cat data/last_success.txt
```

VM yeniden başlasa bile `restart: unless-stopped` ile konteynerler ayağa kalkar.

### D) Güvenlik ipuçları

- `.env` dosyasını **asla** Git’e commit etme (zaten `.gitignore`’da).
- SSH key ile gir; parola ile root açma.
- API key / bot token’ı kimseyle paylaşma.

---

## 7) Ortam değişkenleri

`.env.example` tam listedir. Sık kullanılanlar:

| Değişken | Varsayılan | Açıklama |
|----------|------------|----------|
| `API_KEY` | — | checkvisaslots anahtarı (**zorunlu**) |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | — | Ana bildirim |
| `VISA_LOCATIONS` | `ISTANBUL` | API lokasyon adı (virgülle çoklu) |
| `VISA_CATEGORIES` | `B1/B2` | Kategori filtresi |
| `VISA_DURATION_DAYS` | `120` | Kaç gün ileriye bakılsın |
| `CHECK_INTERVAL_MINUTES` | `5` | Döngü taban aralığı |
| `CHECK_JITTER_SECONDS` | `90` | 0–N sn rastgele ek bekleme |
| `PROXY_URL` | `http://proxy:8888` | Forward proxy (`http://` şeması) |
| `CF_SOLVER_URL` | boş | FlareSolverr adresi |
| `SOURCE` | `checkvisaslots` | `official` = Phase-2 stub |
| `DEDUPE_HOURS` | `6` | Aynı slotu tekrar bildirme penceresi |
| `NOTIFY` / `DRY_RUN` | `true` / `false` | Bildirim aç/kapa |
| `TZ` | `Asia/Istanbul` | Saat dilimi |

---

## 8) Çalışma mantığı

```text
[loop + jitter]
    → Tinyproxy
    → curl_cffi (Chrome TLS)  →  checkvisaslots API
    → İstanbul / kategori / tarih filtresi
    → dedupe
    → Telegram (+ e-posta)
```

- 403 / 429 / Cloudflare benzeri cevap → 15 → 30 → 60 dk backoff (`data/backoff.json`)
- API `remaining` çok düşükse aralık otomatik uzar
- Resmi site (`SOURCE=official`) henüz stub’dır; production’da `checkvisaslots` kullan

### Proje yapısı

```text
visa_slot_checker.py          # giriş noktası
src/config.py                 # ortam değişkenleri
src/client.py                 # CF-safe HTTP + backoff
src/checker.py                # slot filtresi
src/dedupe.py                 # tekrar bildirim engeli
src/notify/                   # telegram, email, pushover
src/sources/                  # checkvisaslots + official stub
proxy/                        # Tinyproxy imajı
docker-compose.yml
```

---

## 9) Testler ve sorun giderme

```bash
python3 -m unittest discover -s tests -v
```

| Belirti | Olası neden | Ne yap |
|--------|-------------|--------|
| `Invalid Access Code` | Yanlış / eksik `API_KEY` | checkvisaslots dashboard’dan yenile |
| Telegram mesajı yok | Token/chat id; bota `/start` atılmamış | `getUpdates` ile id doğrula |
| Sürekli 403 | CF / IP | Proxy’yi kontrol et; `docker compose --profile cf up -d` + `CF_SOLVER_URL` |
| Hiç slot yok | Lokasyon adı uyuşmuyor | Logdaki `visa_location` listesine bak, `.env` güncelle |
| Spam bildirim | Dedupe kapalı / sıfırlanmış | `DEDUPE_HOURS` ve `data/last_alert.json` |

Log izleme:

```bash
docker compose logs -f visa-checker
```

---

## 10) Uyarılar

- Bu araç **bilgilendirme** içindir; otomatik randevu **almaz**.
- checkvisaslots ve resmi randevu sitelerinin kullanım şartlarına uy.
- Üçüncü taraf API kotası / Cloudflare kuralları değişebilir.
- Production’da CF sorununda Tinyproxy yerine residential proxy `PROXY_URL` daha etkili olabilir.
- Hesap ban riski nedeniyle otomatik booking bilerek eklenmemiştir.

---

## Katkı ve kaynak

- **Orijinal (Hindistan):** [Abhishekkataria16/USVisaSlotsChecker](https://github.com/Abhishekkataria16/USVisaSlotsChecker) — Abhishek Kataria  
- **Türkiye / İstanbul uyarlaması:** Doruk Doğular — bu fork

İyileştirme önerileri ve PR’lar memnuniyetle karşılanır.

---

## Lisans

Bu proje **MIT License** ile sunulur. Ayrıntılar için [LICENSE](LICENSE) dosyasına bakın.

- Copyright (c) 2025 Abhishek Kataria (orijinal çalışma)  
- Copyright (c) 2026 Doruk Doğular (Türkiye uyarlaması)

```
MIT License — özgürce kullanabilir, değiştirebilir ve dağıtabilirsiniz;
lisans bildirimini korumanız yeterlidir. Yazılım “OLDUĞU GİBİ” sunulur.
```
