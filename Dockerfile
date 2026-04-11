FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxrender1 \
    libxext6 \
    libgomp1 \
    tesseract-ocr \
    libglib2.0-0 \
    libsm6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch and torchvision FIRST (avoids pulling 2.5 GB of NVIDIA CUDA libs)
RUN pip install --no-cache-dir \
    torch==2.2.2+cpu \
    torchvision==0.17.2+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Install remaining Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the SentenceTransformer model to avoid Hugging Face rate limits on Cloud Run
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application code
COPY . .
RUN chmod +x start.sh

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

CMD ["./start.sh"]
