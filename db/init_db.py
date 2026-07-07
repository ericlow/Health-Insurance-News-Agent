"""Creates the database and runs the schema. Run once before first use."""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ['DATABASE_URL']
DB_NAME = 'health_insurance_news'

# Connect to default postgres DB to create our database
base_url = DATABASE_URL.rsplit('/', 1)[0] + '/postgres'
conn = psycopg2.connect(base_url)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()
cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
if not cur.fetchone():
    cur.execute(f'CREATE DATABASE {DB_NAME}')
    print(f'Created database: {DB_NAME}')
else:
    print(f'Database already exists: {DB_NAME}')
cur.close()
conn.close()

# Now run the schema
conn = psycopg2.connect(DATABASE_URL)
schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
with open(schema_path) as f:
    conn.cursor().execute(f.read())
conn.commit()
conn.close()
print('Schema applied.')
