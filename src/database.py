import os

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

load_dotenv()
user = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
database = os.getenv("POSTGRES_DB")
port = os.getenv("POSTGRES_PORT")

DATABASE_URL = f"postgresql://{user}:{password}@localhost:{port}/{database}"

engine = create_engine(DATABASE_URL, echo=True)


def init_db():
    from .models import User

    SQLModel.metadata.create_all(engine)


def get_session():
    """Provides a temporary connection to the database."""
    with Session(engine) as session:
        yield session
