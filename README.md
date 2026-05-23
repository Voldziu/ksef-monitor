# KSeF Monitor

Monitor faktur KSeF — pobiera faktury z Krajowego Systemu e-Faktur w cyklicznych interwałach, zapisuje je lokalnie i wysyła powiadomienia e-mail o nowych dokumentach.

Projekt do samodzielnego hostowania, do użytku prywatnego — głównym celem jest powiadomienie o tym, że pojawiła się nowa faktura.

---

## Architektura

```
            ┌──────────────┐
            │   KSeF API   │
            └──────┬───────┘
                   │ polling co N min (APScheduler)
                   ▼
   ┌───────────────────────────────┐
   │   ksef-monitor (app.main)     │
   │   • pobranie nowych faktur    │
   │   • deduplikacja w SQLite     │
   │   • metryki Prometheus :8000  │
   └───────┬──────────────┬────────┘
           │              │
           ▼              ▼
     ┌──────────┐   ┌──────────────┐
     │  SMTP    │   │  Prometheus  │──▶ Grafana :3000
     │  (mail)  │   │     :9090    │
     └──────────┘   └──────────────┘
```

## Funkcje

- Cykliczne pobieranie faktur z KSeF (domyślnie co 15 min).
- Lokalne przechowywanie w SQLite (`data/invoices.db`) z deduplikacją po numerze KSeF.
- Powiadomienia e-mail (HTML + tekst) z listą nowych dokumentów.
- Wsparcie dla dwóch metod uwierzytelnienia: **token** (KSeF 1.0) oraz **certyfikat + klucz prywatny** (KSeF 2.0).
- Metryki Prometheus na porcie `:8000` i dashboard Grafana na `:3000`.
- MailHog (profil `dev`) do testów wysyłki bez prawdziwego SMTP.

## Wymagania

- Docker + Docker Compose
- NIP podatnika
- Token KSeF **lub** para klucz/certyfikat (zalecane — patrz niżej)
- Działający SMTP (albo MailHog w profilu `dev`)

## Uwierzytelnienie

Aplikacja wspiera dwie metody (wybór przez `KSEF_AUTH_METHOD`):

| Metoda | Wersja KSeF | Dostępność | Wymagane zmienne |
|---|---|---|---|
| `certificate` ✅ **zalecane** | KSeF 2.0 | jedyna metoda od 01.01.2027 | `KSEF_CERT_PATH`, `KSEF_KEY_PATH`, opcjonalnie `KSEF_KEY_PASSWORD` |
| `token` | KSeF 1.0 | działa do 31.12.2026 | `KSEF_TOKEN` |

**Zalecane** jest użycie pary klucz/certyfikat (`.key` + `.crt`) zamiast tokenu — to docelowa metoda KSeF 2.0 i nie wymaga migracji po 31.12.2026.

Klucze umieszczamy w katalogu **`secrets/`** w repozytorium (jest zamontowany do kontenera jako `/workspace/secrets`):

```
secrets/
├── ksef-cert.crt
└── ksef-cert.key
```

Następnie w `.env`:

```env
KSEF_AUTH_METHOD=certificate
KSEF_CERT_PATH=secrets/ksef-cert.crt
KSEF_KEY_PATH=secrets/ksef-cert.key
KSEF_KEY_PASSWORD=        # jeśli klucz jest zaszyfrowany
```

## Szybki start (lokalnie, Docker Compose)

Aplikacja uruchamiana jest wyłącznie przez Docker Compose.

1. **Sklonuj repo i wejdź do katalogu projektu.**

2. **Skopiuj `.env.example` do `.env.{nazwa}` i uzupełnij wartości:**

   ```bash
   cp .env.example .env.{nazwa}
   ```

   Co najmniej: `KSEF_NIP`, dane uwierzytelnienia, adres `MAIL_TO`.

3. **Umieść certyfikat i klucz w `secrets/`** (jeśli używasz `certificate`):

   ```bash
   cp /sciezka/do/twojego.crt secrets/ksef-cert.crt
   cp /sciezka/do/twojego.key secrets/ksef-cert.key
   chmod 600 secrets/*.key
   ```
4. **Nadaj uprawnienia do zapisu katalogowi `data/` i `logs/`** (SQLite będzie tam tworzyć bazę):

   ```bash
   mkdir -p data
   sudo chmod -R 777 ./data
   mkdir -p logs
   sudo chmod -R 777 ./logs
   ```
5. **Uruchom stack:**

   ```bash
   docker compose -p ksef-{name} up -d
   ```

   Z MailHogiem (do testów lokalnych e-maili):

   ```bash
   docker compose -p ksef-{name} --profile dev up -d
   ```

6. **Otwórz UI:**

   | Serwis | URL | Login |
   |---|---|---|
   | Metryki aplikacji | http://localhost:8000/metrics | — |
   | Prometheus | http://localhost:9090 | — |
   | Grafana | http://localhost:3000 | `admin` / `admin` |
   | MailHog (profil `dev`) | http://localhost:8025 | — |

7. **Podejrzyj logi:**

   ```bash
   docker compose -p ksef-{name} logs -f ksef-monitor
   ```

## Konfiguracja (`.env`)

| Zmienna | Opis | Domyślnie |
|---|---|---|
| `KSEF_ENV` | Środowisko KSeF (`test` / `prod`) | `test` |
| `KSEF_NIP` | NIP podatnika | — |
| `KSEF_AUTH_METHOD` | `token` lub `certificate` | `token` |
| `KSEF_TOKEN` | Token API (dla `token`) | — |
| `KSEF_CERT_PATH` | Ścieżka do `.crt`/`.pem` (dla `certificate`) | — |
| `KSEF_KEY_PATH` | Ścieżka do `.key` (dla `certificate`) | — |
| `KSEF_KEY_PASSWORD` | Hasło do klucza (opcjonalne) | — |
| `CHECK_INTERVAL_MINUTES` | Interwał pollingu | `15` |
| `NOTIFICATION_CHANNELS` | Aktywne kanały, JSON list | `["mail"]` |
| `MAIL_HOST`, `MAIL_PORT` | SMTP host/port | `localhost`, `1025` |
| `MAIL_USE_TLS` | TLS dla SMTP | `false` |
| `MAIL_USER`, `MAIL_PASSWORD` | Dane logowania SMTP | — |
| `MAIL_FROM` | Nadawca | — |
| `MAIL_TO` | Odbiorcy, JSON list | — |
| `STORAGE_PATH` | Plik bazy SQLite | `data/invoices.db` |
| `METRICS_ENABLED` | Włącz Prometheus | `true` |
| `METRICS_PORT` | Port metryk | `8000` |
| `PROMETHEUS_PORT` | Port metryk | `9090` |
| `GRAFANA_PORT` | Port metryk | `3000` |
| `LOG_LEVEL` | `DEBUG`/`INFO`/`WARNING`/`ERROR` | `INFO` |
| `LOG_FORMAT` | `text` lub `json` | `text` |

## Skrypty pomocnicze

Skrypty z katalogu `scripts/` uruchamiane są **wyłącznie wewnątrz kontenera** (mają dostęp do tej samej konfiguracji i sekretów):

```bash
docker compose exec ksef-monitor bash
```

A następnie w shellu kontenera:

```bash
# Jednorazowe pobranie faktur (poza harmonogramem)
python scripts/fetch.py

# Wygenerowanie testowej faktury (środowisko test KSeF)
python scripts/simulate_invoice.py
```

Można też uruchomić pojedynczy cykl monitorowania bez wchodzenia do shella:

```bash
docker compose -p ksef-{name} exec ksef-monitor python -m app.main run-once
```

## Monitoring

- **Prometheus** scrapuje `ksef-monitor:8000/metrics` zgodnie z `monitoring/prometheus.yml`.
- **Grafana** ma sprowisionowane datasource i dashboardy w `monitoring/grafana/provisioning/`.
- Logi aplikacji trafiają do `logs/app.log` (z rotacją) i na stdout kontenera.

---

## English (TL;DR)

Self-hosted monitor for the Polish KSeF (Krajowy System e-Faktur) e-invoicing system. Polls KSeF on a schedule, stores invoices in SQLite, and sends e-mail notifications about new documents. Ships with a Prometheus + Grafana stack.

### Requirements

Docker + Docker Compose, taxpayer NIP, and either a KSeF API token or a certificate/key pair.

### Authentication

- `certificate` — **recommended**, KSeF 2.0, the only method available from 2027-01-01.
- `token` — KSeF 1.0, deprecated after 2026-12-31.

Place your `.crt` and `.key` in the `secrets/` directory:

```
secrets/
├── ksef-cert.crt
└── ksef-cert.key
```

### Run

```bash
cp .env.example .env.{nazwa}       # then edit values
docker compose -p ksef-{name} up -d
```

UIs: metrics `:8000/metrics`, Prometheus `:9090`, Grafana `:3000` (`admin`/`admin`), MailHog `:8025` (profile `dev`).

### Helper scripts

Run only inside the container:

```bash
docker compose -p ksef-{name} exec ksef-monitor bash
python scripts/fetch.py
python scripts/simulate_invoice.py
```
