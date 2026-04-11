#!/bin/sh
set -e

echo "[START] Preparing data files..."

# Create data directory
mkdir -p /app/data

# Download FAISS index
if [ -n "$KG_FAISS_SRC" ]; then
  echo "[START] Downloading FAISS index..."
  curl -sL "$KG_FAISS_SRC" -o /tmp/kg_faiss_index.faiss
  echo "[START] FAISS index downloaded ($(wc -c < /tmp/kg_faiss_index.faiss) bytes)"
  export KG_FAISS_INDEX=/tmp/kg_faiss_index.faiss
fi

# Download FAISS metadata
if [ -n "$KG_FAISS_META_SRC" ]; then
  echo "[START] Downloading FAISS metadata..."
  curl -sL "$KG_FAISS_META_SRC" -o /tmp/kg_faiss_metadata.pkl
  echo "[START] FAISS metadata downloaded ($(wc -c < /tmp/kg_faiss_metadata.pkl) bytes)"
  export KG_FAISS_META=/tmp/kg_faiss_metadata.pkl
fi

# Download CSV data files from GCS (only if not already present)
if [ -n "$DRUG_CSV_URL" ] && [ ! -f /app/data/cleaned_clinical_drugs_dataset.csv ]; then
  echo "[START] Downloading drug dataset CSV..."
  curl -sL "$DRUG_CSV_URL" -o /app/data/cleaned_clinical_drugs_dataset.csv
  echo "[START] Drug CSV downloaded ($(wc -c < /app/data/cleaned_clinical_drugs_dataset.csv) bytes)"
fi

if [ -n "$KG_CSV_URL" ] && [ ! -f /app/data/pharmasage_kg_triples_cleaned.csv ]; then
  echo "[START] Downloading KG triples CSV..."
  curl -sL "$KG_CSV_URL" -o /app/data/pharmasage_kg_triples_cleaned.csv
  echo "[START] KG CSV downloaded ($(wc -c < /app/data/pharmasage_kg_triples_cleaned.csv) bytes)"
fi

# Also download KG triplets and strong binders (small files)
if [ -n "$KG_TRIPLETS_URL" ] && [ ! -f /app/data/kg_triplets.csv ]; then
  curl -sL "$KG_TRIPLETS_URL" -o /app/data/kg_triplets.csv
fi

if [ -n "$STRONG_BINDERS_URL" ] && [ ! -f /app/data/strong_binders.csv ]; then
  curl -sL "$STRONG_BINDERS_URL" -o /app/data/strong_binders.csv
fi

echo "[START] Data directory contents:"
ls -la /app/data/ 2>/dev/null || echo "  (empty)"

export FLASK_RELOAD=${FLASK_RELOAD:-false}

echo "[START] Starting Gunicorn..."
exec gunicorn \
  -b 0.0.0.0:${PORT:-8080} \
  --workers=${GUNICORN_WORKERS:-1} \
  --threads=${GUNICORN_THREADS:-4} \
  --timeout=${GUNICORN_TIMEOUT:-120} \
  wsgi:app
