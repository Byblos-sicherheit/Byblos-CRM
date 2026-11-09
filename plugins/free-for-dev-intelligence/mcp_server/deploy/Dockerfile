FROM python:3.13-slim
WORKDIR /app
COPY mcp_server/requirements.txt /app/mcp_server/requirements.txt
RUN pip install --no-cache-dir -r /app/mcp_server/requirements.txt
COPY . /app
ENV HOST=0.0.0.0 PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python3", "mcp_server/free_dev_mcp.py", "--http", "--host", "0.0.0.0", "--port", "8000"]
