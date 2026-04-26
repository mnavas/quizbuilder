# QuizBuilder

Self-hosted online assessment platform. Run your own quiz and test server — spelling bees, multiple-choice exams, reading comprehension, and more. Built with Docker, works offline on a local network.

**[Installation guide →](https://mnavas.github.io/quizbuilder-page/pages/install.html)** · [Examples](https://mnavas.github.io/quizbuilder-page/pages/examples.html) · [Website](https://mnavas.github.io/quizbuilder-page)

---

## Quick start

### 1. Prerequisites

- **Docker Desktop** — [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
- **Python 3** — [python.org/downloads](https://www.python.org/downloads/)

On Linux both can be installed in one step:
```bash
curl -fsSL https://get.docker.com | sh && sudo apt install python3
```

### 2. Download QuizBuilder

```bash
git clone https://github.com/mnavas/quizbuilder.git
cd quizbuilder
```

No Git? Download the [ZIP from GitHub](https://github.com/mnavas/quizbuilder/archive/refs/heads/main.zip) and extract it.

### 3. Install & configure

```bash
# Mac / Linux
./quizbuilder install

# Windows
quizbuilder install
```

The installer checks Docker, sets up passwords, generates a secret key, and starts the server.
Just answer two prompts: your admin email and password. Everything else is automatic.

### 4. Open in your browser

```
http://localhost:3000
```

Log in with the admin email and password you entered during setup.

---

## Daily commands

All commands are run from inside the `quizbuilder` folder.
On **Mac / Linux** prefix with `./` — e.g. `./quizbuilder start`.

| Action | Command |
|--------|---------|
| Start server | `quizbuilder start` |
| Stop server | `quizbuilder stop` |
| Restart | `quizbuilder restart` |
| View logs | `quizbuilder logs` |
| Check status | `quizbuilder status` |
| Update to latest | `quizbuilder update` |
| Show network URLs | `quizbuilder hostname` |

---

## Access from other devices on your network

Run `quizbuilder hostname` (or `./quizbuilder hostname` on Mac/Linux) to list every URL
where QuizBuilder is reachable on your local network.

Students open that URL in their browser — no installation needed on their device.

---

## License

Released under the [GNU General Public License v3.0](LICENSE).
