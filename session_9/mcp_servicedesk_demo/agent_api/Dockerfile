# Build from the demo root:  docker build -f agent_api/Dockerfile -t kernmart-servicedesk/agent-api:v1 .
FROM python:3.12-slim
WORKDIR /app

COPY agent_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Note what is NOT copied: servicedesk_core. This service has no database code and no business rules.
COPY llm.py agent_instructions.py ./
COPY agent_api ./agent_api

USER 10001
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "agent_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
