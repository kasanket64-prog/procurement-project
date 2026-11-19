# ProcureAI — Complete Deployment & Project Guide (No Vercel / No Phone Verification)

## Live Production Deployment (Netlify — Deployed & Verified)

ProcureAI is live publicly on **Netlify** (both React frontend and `/api/*` serverless endpoints on a single origin, with visitor access set to Public):

| Item | Live Value |
| --- | --- |
| **Live Website URL** | `https://procureai-platform.netlify.app/` |
| **Live Health API** | `https://procureai-platform.netlify.app/api/health` |
| **Live Suppliers API** | `https://procureai-platform.netlify.app/api/suppliers` (`361` total: `248` Public source + `113` Simulated) |
| **Live Catalog API** | `https://procureai-platform.netlify.app/api/catalog?q=bearing` |
| **Live Compare API** | `https://procureai-platform.netlify.app/api/compare?id=SIM-201&id=SUP-038` |
| **Live Quotation Demo API** | `https://procureai-platform.netlify.app/api/quotes/demo` |
| **Live Quotation Total API** | `POST https://procureai-platform.netlify.app/api/quotes/total` |
| **Live Quotation Review API** | `POST https://procureai-platform.netlify.app/api/quotes/review` |
| **Netlify Site ID** | `b42166a6-8a9a-4fff-82a8-dd647e01827a` |
| **Netlify Deploy ID** | `6aff3c2fb7a9e52036fe5880` (`state: ready`, Node `nodejs24.x`) |
| **Netlify Permalink** | `https://6aff3c2fb7a9e52036fe5880--procureai-platform.netlify.app/` |
| **Netlify Dashboard** | `https://app.netlify.com/projects/procureai-platform` |

### Verified Live HTTP Checks (`https://procureai-platform.netlify.app`)
- `GET /` -> `200` (`<div id="root"></div>` present)
- `GET /api/health` -> `200` (`{"status":"ok"}`)
- `GET /api/suppliers?limit=5` -> `200` (`total=361`)
- `GET /api/suppliers?source=public&limit=2` -> `200` (`total=248`)
- `GET /api/suppliers?source=simulated&limit=2` -> `200` (`total=113`)
- `POST /api/quotes/total` (`quantity=100`, `unit_price=100`, `freight=1500`) -> `200` (`{"subtotal":"10000","total":"11500","missing":[]}`)
- `GET /api/catalog?q=bearing` -> `200` (`count=1`)
- `GET /api/compare?id=SIM-201&id=SUP-038` -> `200` (`count=2`)
- `GET /api/quotes/demo` -> `200` (`eligible=1`)

---

## 1. Alternative Option: Single-URL Full-Stack Deployment on Render

Because `ml/api.py` now serves the production React build from `static/` alongside `/api/*`, deploying **one** Render Python Web Service hosts **both the frontend UI and backend API** on a single HTTPS URL:
- **No Vercel account needed**
- **No `VITE_API_BASE_URL` build configuration needed** (the frontend automatically uses `window.location.origin` when served from a non-`5173` / non-`github.io` origin)
- **No cross-origin CORS configuration needed** when using the unified URL

### Render Dashboard Settings (Repo: `kasanket64-prog/procurement-project`)
Connect your GitHub repository in Render (`New` -> `Web Service` -> `kasanket64-prog/procurement-project`), or use Blueprint (`render.yaml`):

| Setting | Value |
| --- | --- |
| **Branch** | `hosted-demo-api` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r real-pilot/requirements.txt` |
| **Start Command** | `python ml/api.py` |
| **Health Check Path** | `/api/health` |
| **Plan** | `Free` |

### Environment Variables on Render
Already declared in `render.yaml`:
- `HOST=0.0.0.0` (also auto-selected in `ml/api.py` whenever `PORT` or `RENDER` is set)
- `ALLOWED_ORIGINS=*` (supports comma-separated exact origins or wildcard patterns such as `https://kasanket64-prog.github.io`)

### Post-Deploy Verification URLs
Once Render finishes deploying and assigns your unique HTTPS domain (referred to below as `https://<your-render-service>.onrender.com`):
1. **Website UI**: `https://<your-render-service>.onrender.com/`
2. **Health Check**: `https://<your-render-service>.onrender.com/api/health` -> expects `{"status": "ok"}`
3. **Suppliers API**: `https://<your-render-service>.onrender.com/api/suppliers?limit=5` -> expects `total: 361`

> **Note:** Do not hardcode `https://procureai-api.onrender.com` unless Render assigned that exact URL to your own account — that subdomain is already occupied by an unrelated Express service.

---

## 2. Option B: GitHub Pages (Frontend) + Render (Backend)

A GitHub Actions workflow is already included at `.github/workflows/deploy-pages.yml` to publish the built `static/` folder to GitHub Pages using your existing GitHub account (`kasanket64-prog`), with no phone verification needed.

### Steps
1. Open your GitHub repository `kasanket64-prog/procurement-project` -> **Settings** -> **Pages**.
2. Under **Build and deployment** -> **Source**, choose **GitHub Actions**.
3. Trigger or wait for the **Deploy ProcureAI Static Frontend to GitHub Pages** workflow to finish (or run it manually under **Actions** -> **Run workflow** on branch `hosted-demo-api`).
4. Open your GitHub Pages site with your Render backend URL appended once via `?api=`:
   ```text
   https://kasanket64-prog.github.io/procurement-project/?api=https://<your-render-service>.onrender.com
   ```
   `resolveApiBase()` in `src/Workspace.tsx` automatically saves the `?api=` URL to `localStorage` under `procureai-api-base`, so subsequent visits to `https://kasanket64-prog.github.io/procurement-project/` remember the backend automatically.
5. *(Recommended CORS tightening on Render)*: Set `ALLOWED_ORIGINS=https://kasanket64-prog.github.io` in Render's Environment tab if hosting the UI on GitHub Pages.

---

## 3. Option C: Manual Static Folder Upload

Because `vite.config.ts` now builds with `base: './'` (relative asset URLs) and runtime `?api=` / `localStorage` API resolution:
1. Built static files live in both:
   - `C:\Users\sanke\.gemini\antigravity\scratch\procureai-landing-page\dist`
   - `C:\Users\sanke\.gemini\antigravity\scratch\procurement-backend\static`
2. Any static host (e.g., Netlify Drop, Cloudflare Pages, GitHub Pages, S3/R2 static bucket, or any Nginx/Apache server) can serve that folder directly.
3. Visit the deployed URL once with `?api=https://<your-render-service>.onrender.com` appended.

---

## 4. Local Repositories & Key Files

### Backend + Unified Host Repository
- **Path**: `C:\Users\sanke\.gemini\antigravity\scratch\procurement-backend`
- **GitHub Remote**: `https://github.com/kasanket64-prog/procurement-project`
- **Active Branch**: `hosted-demo-api`
- **Key Files**:
  - `ml/api.py` — Unified HTTP server serving `/api/*` endpoints and static frontend files from `static/` (`serve_static`, `filter_suppliers`, `cors_origin`, `quote_total`)
  - `ml/simulated_suppliers.py` — Integrates `dataset/suppliers.csv` + `dataset/supplier_items.csv` (`SUP-001`–`SUP-106`), scenario suppliers (`SIM-201`–`SIM-207`), and `ml/search_catalog.json` (`SIM-CAT-001`–`SIM-CAT-050`)
  - `ml/public_supplier_leads.json` — Preserved 248 public-source supplier records (UK Contracts Finder, OGL v3.0)
  - `ml/catmat_research_catalog.json` — Preserved CATMAT public procurement catalog
  - `ml/test_api.py` — 5 unit tests covering API discovery, quote totals, quote review, fixture isolation/grade matching, and combined public + simulated search/compare
  - `render.yaml` — Render Web Service definition (`HOST=0.0.0.0`, `ALLOWED_ORIGINS=*`, `/api/health`)
  - `static/` — Production Vite bundle (`index.html`, `favicon.png`, `robots.txt`, `assets/*`)
  - `.github/workflows/deploy-pages.yml` — GitHub Pages workflow publishing `./static`

### Frontend Source Repository
- **Path**: `C:\Users\sanke\.gemini\antigravity\scratch\procureai-landing-page`
- **Branch**: `master`
- **Key Files**:
  - `src/Workspace.tsx` — Procurement workspace (`resolveApiBase()`, requirements, supplier discovery, comparison, RFQs, quotation total/review, decision capture, profile; `localStorage` persistence)
  - `src/discovery.ts` — Pure domain helpers (`resolveRequirement`, `extractGrade`, `productKeyword`, `evaluateSupplier`, `canCompare`, `normalizeSupplier`, `displayValue`, `nextSequentialId`, `upsertRecord`, `upsertRequirement`, `parseQuantityUnit`)
  - `src/App.tsx` — Landing + workspace shell
  - `vite.config.ts` — Configured with `base: './'` for portable static/subpath deployment
  - `.env` — Left empty (`VITE_API_BASE_URL=`) so production builds auto-detect same-origin instead of hardcoding localhost; `.gitignore` excludes `.env` from Git
  - `.env.example` — Documented template
  - `test/buyer-flow.test.mjs` — 12 Node unit tests

---

## 5. Dataset Summary & API Endpoints

### Preserved Supplier & Catalog Counts
- **Total Suppliers**: `361`
  - **Public source**: `248` (`source_label: "Public source"`, `source_type: "public"`)
  - **Simulated**: `113` (`source_label: "Simulated"`, `source_type: "simulated"`, comprising `SUP-001`–`SUP-106` + `SIM-201`–`SIM-207`)

### HTTP Endpoints (`ml/api.py`)
| Route | Method | Behavior |
| --- | --- | --- |
| `/` and `/index.html` | `GET` | Serves ProcureAI React UI (`static/index.html`) |
| `/assets/*`, `/favicon.png`, `/robots.txt` | `GET` | Serves built static assets from `static/` |
| `/api/health` | `GET` | Returns `{"status": "ok"}` |
| `/api/suppliers` | `GET` | Filters full dataset (`q`, `product`, `grade`, `match`, `source`, `country`, `offset`, `limit`) |
| `/api/catalog` | `GET` | Searches combined public CATMAT + simulated catalog (`q`) |
| `/api/compare` | `GET` | Returns 2 to 5 suppliers matching distinct `id` query parameters |
| `/api/quotes/demo` | `GET` | Returns evaluated quotation demo payload |
| `/api/quotes/total` | `POST` | Computes `subtotal`, `total`, and `missing` cost components |
| `/api/quotes/review` | `POST` | Evaluates operator-submitted quotation bundle |

---

## 6. Local Commands & Latest Verification Results

### Run Locally
```powershell
# Unified full-stack server (serves UI + API at http://127.0.0.1:8765/)
C:\Users\sanke\AppData\Local\Programs\Python\Python312\python.exe C:\Users\sanke\.gemini\antigravity\scratch\procurement-backend\ml\api.py

# Optional Vite dev server (proxies API calls to http://127.0.0.1:8765 when running on port 5173)
npm --prefix C:\Users\sanke\.gemini\antigravity\scratch\procureai-landing-page run dev -- --port 5173 --host 127.0.0.1
```

### Rebuild & Sync Frontend Bundle into Backend `static/`
```powershell
npm --prefix C:\Users\sanke\.gemini\antigravity\scratch\procureai-landing-page run build
Copy-Item -Recurse -Force C:\Users\sanke\.gemini\antigravity\scratch\procureai-landing-page\dist\* C:\Users\sanke\.gemini\antigravity\scratch\procurement-backend\static\
```

### Observed Verification Results (Current Build)
- **TypeScript check (`tsc --noEmit`)**: Exit code `0`
- **Frontend unit tests (`npm test`)**: **12/12 passed**
- **Frontend production build (`npm run build`)**: Exit code `0` (`dist/index.html`, `dist/assets/index-B3-dY1SH.js`, `dist/assets/index-CIjNYwum.css`)
- **Backend unit tests (`python -m unittest discover -s ml -p "test_*.py" -v`)**: **5/5 passed** (`0.126s`)
- **Unified HTTP verification (`http://127.0.0.1:8765`)**:
  - `GET /` -> `200` (`text/html; charset=utf-8`, `<div id="root"></div>` present)
  - `GET /assets/index-B3-dY1SH.js` -> `200` (`application/javascript; charset=utf-8`)
  - `GET /api/health` -> `200` (`{"status": "ok"}`)
  - `GET /api/suppliers?limit=5` -> `200` (`total=361`)
