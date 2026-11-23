FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 git && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu126
RUN pip install --no-cache-dir omnivoice==0.2.1 pedalboard soundfile huggingface_hub
RUN python -c "import torch, omnivoice; assert '+cu' in torch.__version__, torch.__version__"
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('k2-fsa/OmniVoice', local_dir='/app/model')"
COPY server.py /app/server.py
ENV PORT=8080 PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 MODEL_DIR=/app/model
EXPOSE 8080
CMD ["python", "/app/server.py"]
