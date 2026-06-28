import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

LOCAL_URL = os.getenv("LOCAL_DATABASE_URL")
REMOTE_URL = os.getenv("REMOTE_DATABASE_URL")

local_engine = create_engine(LOCAL_URL, connect_args={"check_same_thread": False})
remote_engine = create_engine(REMOTE_URL) if REMOTE_URL else None

LocalSession = sessionmaker(bind=local_engine, autocommit=False, autoflush=False)
RemoteSession = sessionmaker(bind=remote_engine) if remote_engine else None

class Base(DeclarativeBase):
    pass

def init_db():
    from app.models import usuario,evaluacion 
    Base.metadata.create_all(bind=local_engine)
