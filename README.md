# ai-engineering

This repository contains materials and code for AI Engineering.

## Python Virtual Environment Setup

It's recommended to use a virtual environment to manage dependencies for this project.

### 1. Create a Virtual Environment

Navigate to the project root and run:

```bash
python -m venv venv
```

### 2. Activate the Virtual Environment

*   **On macOS/Linux:**
    ```bash
    source venv/bin/activate
    ```
*   **On Windows:**
    ```bash
    venv\Scripts\activate
    ```

### 3. Install Dependencies & Setup Environment

Once activated, install the required package for this assignment:

```bash
pip install groq
```

You will also need a Groq API key to run the scripts. Get a free key at [https://console.groq.com/keys](https://console.groq.com/keys) and set it in your terminal:

*   **On macOS/Linux:**
    ```bash
    export GROQ_API_KEY="your_api_key_here"
    ```
*   **On Windows (Command Prompt):**
    ```cmd
    set GROQ_API_KEY="your_api_key_here"
    ```
*   **On Windows (PowerShell):**
    ```powershell
    $env:GROQ_API_KEY="your_api_key_here"
    ```

### 4. Deactivate

When you are done working, you can deactivate the environment:

```bash
deactivate
```

---

## GitHub Setup and Commands

### Basic Setup

If you haven't already configured your Git environment, set your name and email:

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### Common Commands

*   **Check Status:** See which files have changed.
    ```bash
    git status
    ```
*   **Create and Switch to a Branch:** Start your work on a new branch.
    ```bash
    git checkout -b <branch_name>
    ```
*   **Add Changes:** Stage files for a commit.
    ```bash
    git add . # Adds all changed files
    git add <file_path> # Adds a specific file
    ```
*   **Commit Changes:** Save the staged changes with a descriptive message.
    ```bash
    git commit -m "Your descriptive commit message"
    ```
*   **Pull Updates:** Fetch and merge changes from the remote repository.
    ```bash
    git pull origin main
    ```
*   **Push Changes:** Upload your local commits to the remote repository.
    ```bash
    git push origin main
    ```
*   **Switch Branches:**
    ```bash
    git checkout main
    ```