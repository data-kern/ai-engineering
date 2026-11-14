# Build from the demo root:  docker build -f mcp_server/Dockerfile -t kernmart-servicedesk/mcp-server:v1 .
FROM python:3.12-slim
WORKDIR /app

# Dependencies first: this layer is cached until requirements.txt changes (same trick as Session 3).
COPY mcp_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY servicedesk_core ./servicedesk_core
COPY mcp_server ./mcp_server

# Never run as root inside the container. A number (not a name) so Kubernetes can verify it is not root.
USER 10001
ENV MCP_HOST=0.0.0.0 MCP_PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "mcp_server/server.py", "--http"]
