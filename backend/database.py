from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

import os

import os

# Change YOUR_PASSWORD to your actual MySQL password
raw_url = os.getenv("DATABASE_URL", "mysql+pymysql://root:#MySQL890@localhost:3306/sentinel_db")
if raw_url.startswith("mysql://"):
    raw_url = raw_url.replace("mysql://", "mysql+pymysql://", 1)

SQLALCHEMY_DATABASE_URL = raw_url

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()