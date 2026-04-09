# Deployment

## Production Setup

### 1. Environment variables

Create `.env` in the project root:

```env
DB_PASSWORD=<strong-random-password>
SECRET_KEY=<64-char-random-hex>
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=<strong-password>
NEXT_PUBLIC_API_URL=https://api.yourdomain.com/api/v1
ALLOWED_ORIGINS=https://yourdomain.com
```

Generate `SECRET_KEY`:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

> `SECRET_KEY` must be stable. Rotating it invalidates all active sessions.

---

### 2. Build and start

```bash
docker compose up -d --build
```

On first startup, the API automatically:
- Applies all Alembic migrations
- Creates the admin user from `ADMIN_EMAIL` / `ADMIN_PASSWORD`

---

### 3. Nginx reverse proxy (recommended)

Put both services behind nginx for TLS termination. Example config:

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    # TLS config (certbot / manual)
    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Web frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

server {
    listen 443 ssl;
    server_name api.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # API
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Increase limit for media uploads (default is 1MB)
    client_max_body_size 55M;
}
```

Alternatively, keep both on the same domain under a path prefix — update `NEXT_PUBLIC_API_URL` accordingly.

---

## Data Volumes

Two Docker volumes are created automatically:

| Volume | Contents |
|---|---|
| `postgres-data` | PostgreSQL data directory |
| `media-data` | Uploaded files (images, audio, video) — mounted at `/data/media` inside the API container |

### Backup

```bash
# Database
docker exec quizbee-db-1 pg_dump -U quizbee quizbee | gzip > quizbee_db_$(date +%Y%m%d).sql.gz

# Media files
docker run --rm -v quizbee_media-data:/data/media -v $(pwd):/backup alpine \
  tar czf /backup/quizbee_media_$(date +%Y%m%d).tar.gz /data/media
```

### Restore

```bash
# Database
gunzip -c quizbee_db_20260408.sql.gz | docker exec -i quizbee-db-1 psql -U quizbee quizbee

# Media files
docker run --rm -v quizbee_media-data:/data/media -v $(pwd):/backup alpine \
  tar xzf /backup/quizbee_media_20260408.tar.gz -C /
```

---

## Database Migrations

Migrations are applied automatically on API startup via `alembic upgrade head`.

To run manually:
```bash
docker compose exec api alembic upgrade head
```

To create a new migration after changing `models/core.py`:
```bash
docker compose exec api alembic revision --autogenerate -m "description"
```

---

## Updating

```bash
git pull
docker compose up -d --build
```

The API will run new migrations on restart.

---

## Logs

```bash
docker compose logs -f api
docker compose logs -f web
```

API logs are structured JSON:
```json
{"time": "2026-04-08 12:00:00,000", "level": "INFO", "message": "{\"method\": \"POST\", \"path\": \"/api/v1/sessions/take/abc\", \"status\": 201, \"duration_ms\": 42}"}
```

---

## Scaling Considerations

The current setup is a single-node Docker Compose deployment — suitable for hundreds of concurrent takers per test.

For larger deployments:
- **Database**: move to a managed PostgreSQL service (RDS, Supabase, etc.) by updating `DATABASE_URL`
- **Media**: replace the local volume with S3-compatible object storage (requires changes to `media.py`)
- **API**: can be scaled horizontally (stateless); JWT auth and async SQLAlchemy support multiple workers
- **Sync mode WebSockets**: currently single-process; scaling horizontally requires a Redis pub/sub layer (deferred)
