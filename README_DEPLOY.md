# MediMatch - GCP Cloud Run Deployment Quickstart

## Build
```
gcloud builds submit --tag gcr.io/PROJECT_ID/medimatch
```

Or run the helper script (uses PROJECT_ID=crafty-plateau-490307-s2 by default):
```
./deploy_cloudrun.sh
```

## Deploy (Cloud Run)
```
gcloud run deploy medimatch \
  --image gcr.io/PROJECT_ID/medimatch \
  --port 8080 \
  --allow-unauthenticated \
  --memory 1Gi --cpu 1
```
Tune CPU/memory upward if RDKit/Gemini workloads need it.

### If mounting FAISS files
- Mount your FAISS files (e.g., via GCS Fuse or a volume) and set:
  - `KG_FAISS_SRC` → path to `kg_faiss_index.faiss` inside the container
  - `KG_FAISS_META_SRC` → path to `kg_faiss_metadata.pkl`
  The `start.sh` wrapper will copy them into `/tmp` and set `KG_FAISS_INDEX`/`KG_FAISS_META` automatically.

## Required env vars (Cloud Run)
- `DATABASE_URL` (e.g., `postgresql+psycopg2://user:pass@host:5432/dbname`)
- `GROQ_API_KEY`
- `SERPER_API_KEY`
- `GEMINI_API_KEY`
- `KG_FAISS_INDEX` path to FAISS index (mount or GCS Fuse)
- `KG_FAISS_META` path to metadata (mount or GCS Fuse)
- `FLASK_RELOAD=false`

## Healthcheck
Endpoint: `/health` returns 200.

## Data & uploads
- Large files under `data/` and user uploads should live in GCS or a mounted volume, not baked into the image.

## Notes
- WSGI entrypoint: `wsgi.py`
- Gunicorn command (in Dockerfile): `gunicorn -b 0.0.0.0:8080 --workers 2 --threads 4 wsgi:app`
