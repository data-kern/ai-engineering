#!/usr/bin/env bash
# Build the four images and deploy everything to the current Kubernetes cluster.
#
#   export GROQ_API_KEY=gsk_...
#   ./k8s/deploy.sh                 # works with Docker Desktop Kubernetes, kind and minikube
#   ./k8s/open.sh                   # opens the screens on localhost
#   ./k8s/teardown.sh               # removes everything
#
# Optional:  SLACK_WEBHOOK_URL=...   LLM_BASE_URL=...   (defaults: no Slack, Groq)
set -euo pipefail

cd "$(dirname "$0")/.."                       # the demo root: Docker builds from here
NS=servicedesk
CONTEXT=$(kubectl config current-context)
echo "Deploying to Kubernetes context: $CONTEXT"

if [ -z "${GROQ_API_KEY:-}" ]; then
  echo "Set GROQ_API_KEY first (free key: https://console.groq.com)"; exit 1
fi

# ---- 1. build the images (they stay in the local Docker, like Session 3) -------------------------
docker build -q -f mcp_server/Dockerfile      -t kernmart-servicedesk/mcp-server:v1 .
docker build -q -f agent_api/Dockerfile       -t kernmart-servicedesk/agent-api:v1 .
docker build -q -f chat_ui/Dockerfile         -t kernmart-servicedesk/chat-ui:v1 .
docker build -q -f staff_console/Dockerfile   -t kernmart-servicedesk/staff-console:v1 .

# A kind cluster runs its own Docker inside, so the images must be copied in. Docker Desktop and minikube need no copy
# (minikube: run `eval $(minikube docker-env)` before this script).
if [[ "$CONTEXT" == kind-* ]]; then
  for image in mcp-server agent-api chat-ui staff-console; do
    kind load docker-image "kernmart-servicedesk/$image:v1" --name "${CONTEXT#kind-}"
  done
fi

# ---- 2. namespace, secrets, configuration files -------------------------------------------------
kubectl apply -f k8s/00-namespace.yaml

# A Secret holds everything that is private. In a company these values come from Key Vault / Secrets Manager.
kubectl -n $NS create secret generic servicedesk-secrets \
  --from-literal=GROQ_API_KEY="$GROQ_API_KEY" \
  --from-literal=LLM_BASE_URL="${LLM_BASE_URL:-https://api.groq.com/openai/v1}" \
  --from-literal=SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}" \
  --from-literal=POSTGRES_PASSWORD=servicedesk \
  --from-literal=DATABASE_URL=postgresql://servicedesk:servicedesk@postgres:5432/servicedesk \
  --from-literal=SESSION_DATABASE_URL=postgresql+asyncpg://servicedesk:servicedesk@postgres:5432/servicedesk \
  --dry-run=client -o yaml | kubectl apply -f -

# ConfigMaps built straight from the same files Docker Compose mounts.
kubectl -n $NS create configmap servicedesk-sql --from-file=servicedesk_core/sql \
  --dry-run=client -o yaml | kubectl apply -f -

# ---- 3. the services --------------------------------------------------------------------------
kubectl apply -f k8s/10-postgres.yaml -f k8s/20-mailpit-phoenix.yaml
kubectl -n $NS rollout status deployment/postgres --timeout=180s
kubectl apply -f k8s/30-mcp-server.yaml -f k8s/31-agent-api.yaml -f k8s/40-uis.yaml

for deployment in mcp-server agent-api chat-ui staff-console mailpit phoenix; do
  kubectl -n $NS rollout status deployment/$deployment --timeout=240s
done

echo
kubectl -n $NS get pods
echo
echo "Done. Run ./k8s/open.sh to reach the screens."
