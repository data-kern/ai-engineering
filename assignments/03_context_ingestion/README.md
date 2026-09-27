# Data Setup Instructions

This directory contains the scripts required to generate the mock data for the **Financial Advisor Microservice** assignment.

---

## 1. PostgreSQL Database Setup & Generation

We need a database to hold the structured client data. 

### Step 1: Install PostgreSQL (Skip if already installed!)
*If you already have PostgreSQL running on your machine (from previous sessions, a local installation, or Docker), you can skip this step entirely and proceed to Step 2!*

If you don't have PostgreSQL installed, choose the method for your operating system:

**For Mac Users (Homebrew):**
```bash
brew install postgresql@18
brew services start postgresql@18
```
*Note: When you install via Homebrew, Postgres automatically creates a superuser using your **Mac Username**, and it has **no password** by default.*

**For Windows Users (Official Installer):**
1. Download the Windows installer from [EnterpriseDB](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads).
2. Run the installer. Leave the port as `5432`.
3. It will ask you to create a password for the default `postgres` superuser. **Remember this password!**

**For Docker Users (Mac/Windows/Linux):**
If you prefer Docker, you can spin up a Postgres database instantly:
```bash
docker run --name apex-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres
```
*Note: This creates a superuser named `postgres` with the password `postgres`.*

### Step 2: Install Python Requirements
You must install the pre-compiled binary version of psycopg2. 
*(Do **not** run `pip install psycopg2`, as this requires C-compilers and often causes build errors like `pg_config executable not found`).*

```bash
pip install psycopg2-binary
```

### Step 3: Run the Generation Script (`generate_financial_db.py`)
This script creates the `apex_financial` database, creates a schema named `advisory`, and populates it with 2,000 mock clients.

**If you already have Postgres installed or used the Windows Installer/Docker:**
You will use the standard `postgres` username and the password you set during installation.
```bash
# Example for Windows/Docker where the password is 'postgres'
DB_USER="postgres" DB_PASS="postgres" DB_PORT="5432" python generate_financial_db.py
```

**If you used Homebrew (Mac):**
You must tell the script to use your Mac username instead of the default `postgres` user. Replace `YOUR_MAC_USERNAME` below:
```bash
DB_USER="YOUR_MAC_USERNAME" DB_PASS="" DB_PORT="5432" python generate_financial_db.py
```

Upon successful execution, you will see:
```text
Database 'apex_financial' created successfully.
Creating schema 'advisory'...
Creating tables...
Generating 2,000 mock clients. This may take a few seconds...
Inserting data...
✅ Database setup complete!
```

---

## 2. Viewing Your Data (Database UI)

Postgres runs in the background without a graphical interface. To view your data, you should install a Database GUI like **DBeaver**.

### Installing and Connecting via DBeaver
1. **Download:** Go to [dbeaver.io](https://dbeaver.io/) and download the free Community Edition (works on Mac and Windows).
2. **Open DBeaver:** Click the **New Database Connection** button (plug icon in top left) and select **PostgreSQL**.
3. **Connection Settings:**
   * **Host:** `localhost`
   * **Port:** `5432`
   * **Database:** `apex_financial`
   * **Username:** Use your Mac Username (if Homebrew) OR `postgres` (if Windows/Docker).
   * **Password:** Leave blank (if Homebrew) OR enter your password (if Windows/Docker).
4. **Connect:** Click "Finish" or "Test Connection".
5. **View Data:** Expand `apex_financial` -> `Schemas` -> `advisory` -> `Tables`. Right-click on `clients` and select **View Data** to see your 2,000 generated clients!

*(You will notice Client 1042 has exactly the "Conservative" risk tolerance needed for the assignment).*

---

## 3. The Assignment Instructions

Now that your local environment is fully prepared with the database and you have the policy PDF in this folder, you are ready to start coding!

1. Open the main assignment file: `./DataKern_context_ingestion.pdf`
2. Read the scenario carefully. It explains the "Isolated Intern" problem and gives you the exact query you need to answer.
3. Build your solution in a new file (e.g., `main.py`).
4. Ensure you parse the provided `./Apex_Financial_Risk_Policy_2026.pdf` (already included in this folder) to extract the unstructured rules.

---

## 4. How to Submit Your Work

Once you have successfully built, tested, and validated your AI microservice, you must submit it for review.

1. **Commit your code:** Ensure your `main.py`, `Dockerfile`, `requirements.txt`, and Kubernetes `yaml` files are committed to your local git repository. *(Do not commit the large PDF or the database script to your solution branch).*
2. **Push to GitHub:** Push your branch to your remote repository.
3. **Submit the PR:** Create a Pull Request (PR) against the main repository. 
4. **Notify the Instructor:** Tag the instructor in the PR comments for code review. Ensure your PR description includes a screenshot of the Phoenix UI showing a successful LLM trace!
