# 🚀 Easy Vercel Deployment Guide for Krushidhan ERP

Your project is now fully configured for **1-click Vercel Deployment** with `@vercel/python` serverless runtime support, automatic `/tmp` SQLite database initialization, and static asset routing.

---

## ⚡ Method 1: Instant Terminal Deploy (1 Command)

Open your terminal in this project folder (`/Users/virajlengare/akash`) and run:

```bash
npx vercel
```

### Steps during prompt:
1. **Set up and deploy?** → Press `Y` and `Enter`.
2. **Which scope?** → Select your Vercel account.
3. **Link to existing project?** → `N` (or `Y` if you already have one).
4. **What’s your project’s name?** → Press `Enter` (default: `akash` or `krushidhan-erp`).
5. **In which directory is your code located?** → Press `Enter` (`./`).
6. **Want to modify settings?** → `N` (Press `Enter`).

Vercel will build and give you an instant live URL like `https://krushidhan-erp.vercel.app`! 🎉

To deploy directly to production later:
```bash
npx vercel --prod
```

---

## 🐙 Method 2: Automatic Git / GitHub Deployment (Recommended)

1. Push this folder to a GitHub repository:
   ```bash
   git init
   git add .
   git commit -m "Deploy Krushidhan ERP to Vercel"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/krushidhan-erp.git
   git push -u origin main
   ```
2. Go to [https://vercel.com/new](https://vercel.com/new).
3. Import your **`krushidhan-erp`** GitHub repository.
4. Leave all build & output settings as default (Vercel automatically detects `vercel.json` and `api/index.py`).
5. Click **Deploy**.

---

## 📁 Pre-configured Files in the Project:
- [`vercel.json`](file:///Users/virajlengare/akash/vercel.json): Configures the Python serverless function and static asset routes.
- [`api/index.py`](file:///Users/virajlengare/akash/api/index.py): Entrypoint for FastAPI app on Vercel.
- [`.vercelignore`](file:///Users/virajlengare/akash/.vercelignore): Excludes virtual environment and test cache from upload bundle.
- [`requirements.txt`](file:///Users/virajlengare/akash/requirements.txt): Required Python dependencies for Vercel build.
