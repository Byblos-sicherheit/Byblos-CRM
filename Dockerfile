FROM python:3.11-slim

LABEL maintainer="Byblos Sicherheitsdienst"
LABEL description="Byblos CRM v2"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl sqlite3 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir \
    streamlit pandas openpyxl reportlab "qrcode[pil]" Pillow \
    scikit-learn cryptography fastapi uvicorn python-multipart \
    requests psutil \
    && pip install --no-cache-dir pikepdf || true

COPY . .

RUN mkdir -p data backups generated/invoices generated/payroll \
             generated/reports imports assets .streamlit

RUN printf '[server]\nport=8501\nheadless=true\naddress="0.0.0.0"\n\n[browser]\ngatherUsageStats=false\n\n[theme]\nprimaryColor="#c0392b"\nbackgroundColor="#0e1117"\nsecondaryBackgroundColor="#1a1f2e"\ntextColor="#e8eaf0"\n' > .streamlit/config.toml

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

EXPOSE 8501

CMD ["python3", "-m", "streamlit", "run", "app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
