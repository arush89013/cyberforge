from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Fetch the database URL from environment variable (set this in Render's dashboard)
# Falls back to local MySQL for local development
raw_url = os.getenv("DATABASE_URL", "mysql+pymysql://root:#MySQL890@localhost:3306/sentinel_db")

# Ensure we use the pymysql driver (TiDB/Render may provide a plain mysql:// URL)
if raw_url.startswith("mysql://"):
    raw_url = raw_url.replace("mysql://", "mysql+pymysql://", 1)

# TiDB Serverless requires SSL - add SSL params if connecting to TiDB cloud
is_tidb = "tidbcloud.com" in raw_url
if is_tidb:
    connect_args = {
        "ssl": {
            "verify_cert": True,
            "verify_identity": True,
        }
    }
else:
    connect_args = {}

engine = create_engine(
    raw_url,
    pool_pre_ping=True,
    connect_args=connect_args,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()