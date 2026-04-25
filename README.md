# Quizbee

Self-hosted online assessment platform. Run your own quiz and test server — spelling bees, multiple-choice exams, reading comprehension, and more. Built with Docker, works offline on a local network.

**[Installation guide →](pages/install.html)** · [Examples](pages/examples.html) · [GitHub](https://github.com/mnavas/quizbuilder)

---

## Quick start

### 1. Prerequisites

Install **Docker Desktop**: [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)

- Windows: download and run the installer, restart if asked
- Mac: download the `.dmg`, drag to Applications, launch Docker Desktop
- Linux: `curl -fsSL https://get.docker.com | sh`

### 2. Download Quizbee

```bash
git clone https://github.com/mnavas/quizbuilder.git
cd quizbee
```

No Git? Download the [ZIP from GitHub](https://github.com/mnavas/quizbuilder/archive/refs/heads/main.zip) and extract it.

### 3. Configure

```bash
# Windows
copy .env.example .env

# Mac / Linux
cp .env.example .env
```

Open `.env` in any text editor and set your passwords:

```
DB_PASSWORD=your_database_password
SECRET_KEY=your_long_random_secret_key
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your_admin_password
```

Generate a SECRET_KEY with:
```bash
# Mac / Linux
openssl rand -hex 32

# Windows PowerShell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }) -as [byte[]])
```

### 4. Start the server

```bash
docker compose up -d
```

Open your browser: **http://localhost:3000**

Log in with the ADMIN_EMAIL and ADMIN_PASSWORD you set above.

---

## Daily commands

| Action | Command |
|--------|---------|
| Start server | `docker compose up -d` |
| Stop server | `docker compose down` |
| Restart | `docker compose restart` |
| View logs | `docker compose logs -f` |
| Check status | `docker compose ps` |

## Update to the latest version

```bash
git pull origin main
docker compose build
docker compose up -d
```

Your data is stored in Docker volumes and is not affected by updates.

---

## Access from other devices on your network

Find your computer's IP address:
```bash
# Windows
ipconfig

# Mac / Linux
hostname -I
```

Students open `http://YOUR_IP:3000` in their browser. No installation needed on their device.

---

## License

Released under the [GNU General Public License v3.0](LICENSE).
