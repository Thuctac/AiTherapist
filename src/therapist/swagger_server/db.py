import os
from sqlalchemy import create_engine, MetaData, Table

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(DATABASE_URL)
metadata = MetaData()

# reflect existing tables
users = Table("users", metadata, autoload_with=engine)
conversations = Table("conversations", metadata, autoload_with=engine)
messages = Table("messages", metadata, autoload_with=engine)
ratings = Table("ratings", metadata, autoload_with=engine)

