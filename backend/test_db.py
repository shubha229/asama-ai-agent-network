
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database();")
        )
        print("Connected successfully!")
        print("Database:", result.scalar())

except Exception as error:
    print("Connection failed!")
    print(error)
