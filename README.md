# İstanbul ABD Konsolosluğu Randevu Botu (Hibrit)

İstanbul Amerikan Konsolosluğu için müsait ABD vize randevusu arar; bulunca **Telegram** (ana) ve **Email** (yedek) ile anında bildirir.

## Ne yapar?

1. `checkvisaslots.com` API’sini Cloudflare-dostu TLS fingerprint (`curl_cffi`) + opsiyonel proxy ile sorgular
2. `VISA_LOCATIONS` / `VISA_CATEGORIES` ile filtreler (varsayılan: `ISTANBUL` + `B1/B2`)
3. Aynı slot için tekrar spam atmamak üzere dedupe tutar
4. Rate-limit / CF koruması için **jitter’lı aralık** + 403/429’da exponential backoff uygular
5. (Opsiyonel Phase-2) resmi `ustraveldocs.com` kaynağı için stub bırakır — **otomatik randevu almaz**

## Hızlı başlangıç

```bash
cp .env.example .env
# API_KEY, TELEGRAM_*, SMTP_* değerlerini doldur

docker compose up -d --build
docker compose logs -f visa-checker
```

### Proxy smoke test

```bash
docker compose up -d proxy
docker compose run --rm -e PROXY_URL=http://proxy:8888 visa-checker \
  python -m src proxy-test
```

Docker yoksa lokal basit proxy:

```bash
python scripts/simple_proxy.py --port 8888 &
PROXY_URL=http://127.0.0.1:8888 python -m src proxy-test
```

## Önemli env değişkenleri

| Değişken | Varsayılan | Açıklama |
|----------|------------|----------|
| `SOURCE` | `checkvisaslots` | `official` Phase-2 stub |
| `VISA_LOCATIONS` | `ISTANBUL` | API `visa_location` exact match (virgülle çoklu) |
| `VISA_CATEGORIES` | `B1/B2` | Kategori whitelist |
| `CHECK_INTERVAL_MINUTES` | `5` | Loop taban aralığı |
| `CHECK_JITTER_SECONDS` | `90` | Rastgele ek bekleme (0..N) |
| `PROXY_URL` | `http://proxy:8888` | Forward proxy (`http://` şeması) |
| `CF_SOLVER_URL` | boş | FlareSolverr (`--profile cf`) |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | — | Ana bildirim |
| `DEDUPE_HOURS` | `6` | Aynı slotu tekrar bildirme penceresi |
| `REQUIRE_BOTH_CONSULATE_AND_VAC` | `false` | Hindistan legacy AND kuralı |

İlk dry-run’da API’deki gerçek lokasyon string’lerini logda göreceksin:

```bash
DRY_RUN=true NOTIFY=false RUN_MODE=once python -m src once
```

## Mimari

```
visa_slot_checker.py          # entry (cron / loop)
src/config.py                 # env
src/client.py                 # curl_cffi + FlareSolverr + backoff
src/checker.py                # İstanbul filtre
src/dedupe.py                 # alert dedupe
src/notify/{telegram,email,pushover}.py
src/sources/{checkvisaslots,official}.py
proxy/                        # Tinyproxy image
```

## Cloudflare / rate limit

- Chrome TLS impersonation (`curl_cffi`)
- Proxy üzerinden çıkış
- 403/429/503 → 15→30→60 dk backoff (`data/backoff.json`)
- Interval + jitter; API `remaining` düşükse aralık uzar
- Opsiyonel: `docker compose --profile cf up -d` ve `CF_SOLVER_URL=http://flaresolverr:8191`

## Bildirim örneği (Telegram)

```
İstanbul — randevu slotu bulundu

Lokasyon: ISTANBUL
Kategori: B1/B2
Slot sayısı: 3
Başlangıç: 17 Feb 2026
Güncelleme: 2026-02-17 15:30:00 +03
Hemen kontrol et: https://www.ustraveldocs.com/tr
```

## Testler

```bash
python -m unittest discover -s tests -v
```

## Uyarılar

- Bu bot **sadece bildirir**; randevu **otomatik almaz** (ban riski).
- `SOURCE=official` henüz stub’dır; production’da `checkvisaslots` kullan.
- Production CF bypass için Tinyproxy yerine residential proxy `PROXY_URL` önerilir.
- Üçüncü taraf API ve resmi site ToS’una kendi sorumluluğunda uy.
