from typing import Annotated

from sqlmodel import SQLModel, Session
from app.db.db import engine
from fastapi import Depends

def get_session():
    with Session(engine) as session:
        yield session
SessionDep = Annotated[Session, Depends(get_session)]