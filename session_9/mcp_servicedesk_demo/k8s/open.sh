#!/usr/bin/env bash
# Make the screens reachable on localhost. Keep this terminal open; Ctrl+C stops the forwards.
#   8501 chat   8502 staff console   6006 Phoenix   8025 Mailpit   8030 MCP server
set -euo pipefail
NS=servicedesk
trap 'kill 0' EXIT

kubectl -n $NS port-forward svc/chat-ui 8501:8501 &
kubectl -n $NS port-forward svc/staff-console 8502:8502 &
kubectl -n $NS port-forward svc/phoenix 6006:6006 &
kubectl -n $NS port-forward svc/mailpit 8025:8025 &
kubectl -n $NS port-forward svc/mcp-server 8030:8000 &       # lets step02_call_it.py / step04 reach the server in the cluster

echo "Chat: http://localhost:8501   Staff: http://localhost:8502"
echo "Phoenix: http://localhost:6006   Mailpit: http://localhost:8025"
wait
