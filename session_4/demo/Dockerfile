FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for psycopg2
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# ── Layer 1: install Python dependencies ─────────────────────────────────────
# Copied BEFORE source code so Docker reuses this layer on code-only changes.
# (If only app/*.py changes, this pip install layer is served from cache —
#  build time: 3 seconds instead of 3 minutes.)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Layer 2: Pre-download the embedding model ─────────────────────────────────
# Baking the model into the image avoids a 80MB download at runtime.
# The model is stored at /root/.cache/torch/sentence_transformers/
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# ── Layer 3: copy source code ─────────────────────────────────────────────────
COPY ./app /app/app

EXPOSE 8000

# Start the FastAPI service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
