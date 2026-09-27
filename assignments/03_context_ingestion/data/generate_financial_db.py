import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import random
import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = "apex_financial"
SCHEMA_NAME = "advisory"

def create_database():
    try:
        # Connect to default postgres database to create the new one
        conn = psycopg2.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
            dbname="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if DB exists
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
        exists = cursor.fetchone()
        
        if exists:
            print(f"Database '{DB_NAME}' already exists. Recreating...")
            cursor.execute(f"DROP DATABASE {DB_NAME}")
            
        cursor.execute(f"CREATE DATABASE {DB_NAME}")
        cursor.close()
        conn.close()
        print(f"Database '{DB_NAME}' created successfully.")
    except Exception as e:
        print(f"Error creating database: {e}")
        print("Please ensure PostgreSQL is running and credentials are correct.")
        exit(1)

def populate_database():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
            dbname=DB_NAME
        )
        cursor = conn.cursor()
        
        print(f"Creating schema '{SCHEMA_NAME}'...")
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME};")
        cursor.execute(f"SET search_path TO {SCHEMA_NAME};")
        
        print("Creating tables...")
        cursor.execute("""
        CREATE TABLE clients (
            client_id SERIAL PRIMARY KEY,
            first_name VARCHAR(50),
            last_name VARCHAR(50),
            email VARCHAR(100),
            risk_tolerance VARCHAR(20)
        );
        """)
        
        cursor.execute("""
        CREATE TABLE portfolios (
            portfolio_id SERIAL PRIMARY KEY,
            client_id INT REFERENCES clients(client_id),
            cash_balance DECIMAL(15,2),
            total_value DECIMAL(15,2)
        );
        """)
        
        cursor.execute("""
        CREATE TABLE portfolio_holdings (
            holding_id SERIAL PRIMARY KEY,
            portfolio_id INT REFERENCES portfolios(portfolio_id),
            ticker VARCHAR(10),
            shares INT,
            average_buy_price DECIMAL(10,2)
        );
        """)
        
        print("Generating 2,000 mock clients. This may take a few seconds...")
        risk_levels = ['Conservative', 'Moderate', 'Aggressive']
        first_names = ['John', 'Jane', 'Michael', 'Emily', 'Chris', 'Sarah', 'David', 'Jessica', 'Daniel', 'Ashley', 'Uma', 'Kiran']
        last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
        
        # We will do batch inserts for speed
        client_values = []
        portfolio_values = []
        holding_values = []
        tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK.B', 'JNJ', 'V']
        
        for i in range(1, 2001):
            fname = random.choice(first_names)
            lname = random.choice(last_names)
            email = f"{fname.lower()}.{lname.lower()}{i}@example.com"
            risk = random.choice(risk_levels)
            
            # Hardcode the target client 1042
            if i == 1042:
                risk = "Conservative"
                fname = "Target"
                lname = "Client"
                email = "target.client1042@apex.com"
                
            client_values.append((i, fname, lname, email, risk))
            
            # Portfolio logic
            cash = round(random.uniform(1000, 50000), 2)
            equity = round(random.uniform(10000, 500000), 2)
            
            if i == 1042:
                cash = 10000.00
                equity = 90000.00
                
            total = cash + equity
            portfolio_values.append((i, i, cash, total))
            
            # Holdings logic
            num_holdings = random.randint(1, 5)
            for _ in range(num_holdings):
                ticker = random.choice(tickers)
                shares = random.randint(10, 500)
                price = round(random.uniform(50, 500), 2)
                
                # Skip TSLA for 1042 so we can explicitly add a tiny bit
                if i == 1042 and ticker == 'TSLA':
                    continue
                    
                holding_values.append((i, ticker, shares, price))
        
        # Explicitly give client 1042 some TSLA
        holding_values.append((1042, 'TSLA', 10, 200.00))

        # Execute Inserts
        print("Inserting data...")
        cursor.executemany("INSERT INTO clients (client_id, first_name, last_name, email, risk_tolerance) VALUES (%s, %s, %s, %s, %s)", client_values)
        cursor.executemany("INSERT INTO portfolios (portfolio_id, client_id, cash_balance, total_value) VALUES (%s, %s, %s, %s)", portfolio_values)
        cursor.executemany("INSERT INTO portfolio_holdings (portfolio_id, ticker, shares, average_buy_price) VALUES (%s, %s, %s, %s)", holding_values)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Database setup complete!")
        print(f"You can verify by connecting to postgres: psql -U {DB_USER} -d {DB_NAME}")
        print(f"Data is located in the '{SCHEMA_NAME}' schema.")
        
    except Exception as e:
        print(f"Error populating database: {e}")

if __name__ == "__main__":
    create_database()
    populate_database()
