# Build from the demo root:  docker build -f staff_console/Dockerfile -t kernmart-servicedesk/staff-console:v1 .
FROM python:3.12-slim
WORKDIR /app

COPY staff_console/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY servicedesk_core ./servicedesk_core
COPY staff_console ./staff_console

USER 10001
ENV HOME=/tmp PYTHONUNBUFFERED=1
EXPOSE 8502
CMD ["streamlit", "run", "staff_console/app.py", "--server.port=8502", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]
