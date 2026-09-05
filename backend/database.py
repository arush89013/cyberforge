from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Change YOUR_PASSWORD to your actual MySQL password
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:#MySQL890@localhost:3306/sentinel_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()