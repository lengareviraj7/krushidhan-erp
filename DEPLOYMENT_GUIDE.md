# 🚀 Krushidhan Agri-Input Shop ERP - Deployment Guide

This guide walks you through deploying **Krushidhan Agri-Input Shop ERP** online and accessing it from your mobile phone, tablet, or home PC.

---

## 🌟 Option 1: 100% Free Cloudflare Tunnel (Recommended for Shop PC)
*Run directly on your shop computer with zero cloud hosting bills while accessing securely from your mobile phone anywhere.*

1. Download **Cloudflared** on your PC (or run via terminal):
   ```bash
   # On Mac:
   brew install cloudflared
   # On Windows: Download cloudflared.exe
   ```
2. Start the tunnel pointing to your local ERP port:
   ```bash
   cloudflared tunnel --url http://127.0.0.1:8008
   ```
3. Cloudflare will give you an instant public HTTPS URL like:
   `https://random-subdomain.trycloudflare.com`
4. Open that URL on your mobile phone or tablet to use your ERP from anywhere!

---

## ☁️ Option 2: Render.com Cloud Deployment (1-Click Git)
*Best for pure cloud hosting with automated SSL and persistent disk storage.*

1. Push this repository to **GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial Krushidhan ERP commit"
   git push origin main
   ```
2. Sign in to [Render.com](https://render.com).
3. Click **New +** -> **Web Service** and connect your GitHub repository.
4. Render will automatically detect `render.yaml` with:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn src.app:app --host 0.0.0.0 --port $PORT`
   - **Persistent Disk**: Mounted at `/app/data` (1GB) so your SQLite database is never lost across server restarts.
5. Click **Deploy Web Service** — you'll get a live URL like `https://krushidhan-erp.onrender.com`.

---

## 🐳 Option 3: Docker & Cloud Run / VPS
*Best for custom Linux VPS (DigitalOcean, Linode, AWS EC2) or Google Cloud Run.*

### Run locally or on VPS with Docker Compose:
```bash
docker-compose up -d --build
```
Your ERP will be available at `http://localhost:8008` with persistent data in `./data/agri_erp.db`.

### Deploy to Google Cloud Run:
```bash
gcloud run deploy krushidhan-erp \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated \
  --port 8008
```

---

## 📱 Mobile Responsiveness Features Included:
- **Responsive Navigation**: Touch-friendly scrollable tab bar on mobile screens.
- **Stacked Counter Billing**: High-contrast, touch-optimized inputs and sticky bill totals.
- **📲 1-Click WhatsApp Payment Reminder**: Click **"📲 WhatsApp Due"** inside any farmer statement to open WhatsApp with a pre-formatted Marathi reminder text.
- **Full-Screen Farmer Statements**: Touch drawers for viewing purchase details and goods particulars.
