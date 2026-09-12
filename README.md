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

### 3. Install Dependencies

Once activated, install any required packages (if a `requirements.txt` is available):

```bash
pip install -r requirements.txt
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
*   **Create a New Branch:** Start working on a new feature.
    ```bash
    git checkout -b feature/your-feature-name
    ```
*   **Switch Branches:**
    ```bash
    git checkout main
    ```