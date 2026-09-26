# River Bank AI Service & Phoenix Tracing

This guide covers how to set up the complete architecture:
1. **Local Tools:** Arize Phoenix (Tracing) and Streamlit Client UI.
2. **AI Service Backend:** Running the FastAPI app in three modes (Local Python, Local Docker, or Kubernetes).

---

## Part A: Start Local Tools

These components always run locally on your machine.

### 1. Start Phoenix Tracing Server
Arize Phoenix monitors and traces the AI model requests.
We recommend running it locally via Python in a virtual environment.

**Open a terminal and set up the main environment:**
```bash
# Navigate to the class room folder
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Phoenix and start it
pip install arize-phoenix
python -m phoenix.server.main serve
```
*Phoenix UI will be accessible at [http://localhost:6006](http://localhost:6006).*

*(Alternatively, run it via Docker: `docker run -d -p 6006:6006 -p 4317:4317 --name phoenix arizephoenix/phoenix:latest`)*

### 2. Start the Client UI (Streamlit)
The frontend client provides a chat interface to interact with the AI Service.

**Open a NEW terminal, activate the same environment, and run the client:**
```bash
cd client
source ../venv/bin/activate  # On Windows: ..\venv\Scripts\activate

# Install client requirements
pip install streamlit requests

# Run the UI
streamlit run app.py
```
*The Streamlit UI will open in your browser at [http://localhost:8501](http://localhost:8501).*

*(Note: The client will show connection errors until you start the AI Service in Part B.)*

---

## Part B: Run the AI Service (FastAPI)

The backend FastAPI service can be run in one of three ways depending on what you want to test. In all modes, it exposes the API on `localhost:8000`, which the Streamlit UI connects to.

### Level 1: Run Direct FastAPI Locally (Without Docker)

This is the fastest way to develop and test changes.

1. **Open a NEW terminal and navigate to the `ai_service` directory:**
   ```bash
   cd ai_service
   source ../venv/bin/activate
   ```
2. **Install backend dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. **Set your Groq API key:**
   ```bash
   export GROQ_API_KEY="your-groq-api-key-here"
   ```
   *(On Windows Command Prompt use `set GROQ_API_KEY=...` and for PowerShell use `$env:GROQ_API_KEY="..."`)*

4. **Start the FastAPI server:**
   ```bash
   uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   ```
*You can now use the local Streamlit UI to talk to this local backend!*

---

### Level 2: Run Using Docker (Local Container)

If the local FastAPI server from Level 1 is running, stop it by pressing `Ctrl+C`.

1. **Navigate to the `ai_service` directory:**
   ```bash
   cd ai_service
   ```
2. **Build the Docker image:**
   ```bash
   docker build -t riverbank-ai-service:v1 .
   ```
3. **Run the Docker container:**
   Pass the environment variable to the container:
   ```bash
   docker run -d -p 8000:8000 -e GROQ_API_KEY="your-groq-api-key-here" --name ai-service riverbank-ai-service:v1
   ```
*Now, the Streamlit UI (running locally) will communicate with the API running inside the Docker container.*

**To stop:**
```bash
docker stop ai-service
docker rm ai-service
```

---

### Level 3: Run in Kubernetes

If you have a local Kubernetes cluster running (e.g., Docker Desktop, Minikube). Make sure your Docker container from Level 2 is stopped.

1. **Navigate to the `k8s` directory:**
   ```bash
   cd k8s
   ```
2. **Ensure your Docker image is available:**
   If using Docker Desktop, the `riverbank-ai-service:v1` built in Level 2 is already available. 
   *(For Minikube: `eval $(minikube docker-env) && cd ../ai_service && docker build -t riverbank-ai-service:v1 .`)*
3. **Verify the Secret:**
   Check `01-secret.yaml` and update the `GROQ_API_KEY` under `stringData` if you want to use your own key instead of the default placeholder.
4. **Deploy to Kubernetes:**
   ```bash
   kubectl apply -f 01-secret.yaml
   kubectl apply -f 02-deployment.yaml
   kubectl apply -f 03-service.yaml
   ```
5. **Verify the deployment:**
   ```bash
   kubectl get pods
   kubectl get services
   ```
*The local Streamlit client will seamlessly connect to Kubernetes via the `LoadBalancer`, which maps Kubernetes port 8000 back to your `localhost:8000` (on Docker Desktop).*
*(For Minikube, you might need to run `minikube tunnel` in a separate window).*

**Clean up:**
```bash
kubectl delete -f 03-service.yaml
kubectl delete -f 02-deployment.yaml
kubectl delete -f 01-secret.yaml
```
