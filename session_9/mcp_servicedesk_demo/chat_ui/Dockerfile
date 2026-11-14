# Build from the demo root:  docker build -f chat_ui/Dockerfile -t kernmart-servicedesk/chat-ui:v1 .
FROM python:3.12-slim
WORKDIR /app

COPY chat_ui/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY chat_ui ./chat_ui

USER 10001
ENV HOME=/tmp PYTHONUNBUFFERED=1
EXPOSE 8501
CMD ["streamlit", "run", "chat_ui/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]
