# 🚀 AI Engineering Session 3: Testing Guide & README

Welcome! You've just written the code to decouple an AI service, containerized it with Docker, and mapped out a Kubernetes orchestration layer. 

This guide will walk you through exactly how to bind it all together, test your work, and prove that everything functions as expected.

---

## 🛠️ Step 1: Run the API Locally (Sanity Check)
Before we containerize, let's make sure your Python code works.
1. Open a terminal and navigate to this `exercises` folder.
2. Ensure your API key is set: 
   `export GROQ_API_KEY="gsk_your_api_key_here"`
3. Start the FastAPI server:
   ```bash
   uvicorn exercise_03_main:app --reload --port 8000
   ```
4. Open your browser to `http://localhost:8000/docs`. 
5. Test the `/health` endpoint. It should return `{"status": "healthy"}`.
6. Test the `/api/v1/chat` endpoint. Send a JSON body with a `message`. 
7. **Press `CTRL+C`** in your terminal to stop the local server before moving on to Docker.

---

## 🐳 Step 2: Build and Test Docker
Now let's package your code into an immutable container.
1. Make sure Docker Desktop is open and running.
2. In the terminal (inside this `exercises` folder), build your image:
   ```bash
   docker build -t ai-service:v1 -f exercise_04_Dockerfile .
   ```
3. Run the container. Notice how we inject the API key at runtime:
   ```bash
   docker run -p 8000:8000 -e GROQ_API_KEY="$GROQ_API_KEY" ai-service:v1
   ```
4. Check `http://localhost:8000/docs` again. If it works, you are officially running a containerized AI service! 
5. **Press `CTRL+C`** in your terminal to stop the container before moving on to Kubernetes.

---

## ☸️ Step 3: Deploy to Kubernetes
Docker runs your container. Kubernetes keeps it alive.
1. Make sure Kubernetes is enabled in your Docker Desktop settings (you should see a green Kubernetes logo).
2. Apply the three YAML files you wrote:
   ```bash
   kubectl apply -f exercise_05_k8s_secret.yaml
   kubectl apply -f exercise_06_k8s_deployment.yaml
   kubectl apply -f exercise_07_k8s_service.yaml
   ```
3. Check if your pods are running:
   ```bash
   kubectl get pods
   ```
   *You should see two pods showing `1/1 Running`.*

---

## 🦸‍♂️ Step 4: The Self-Healing Demo
Let's prove that Kubernetes actually works.
1. Open a terminal and tell Kubernetes to watch your pods in real-time:
   ```bash
   kubectl get pods -w
   ```
2. Open a **second** terminal window. We are going to simulate a catastrophic failure by deleting a pod. Copy the name of one of your pods and run:
   ```bash
   kubectl delete pod <your-pod-name>
   ```
3. Look back at the first terminal. 
4. **Watch the magic:** Kubernetes will instantly realize that you dropped from 2 pods to 1 pod. It will automatically spawn a brand new replacement pod in seconds to fulfill your "Desired State". 

**Congratulations! You have successfully built and deployed a production-grade, self-healing AI architecture.**
