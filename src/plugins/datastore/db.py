from nonebot import get_driver
from sqlmodel import Session, SQLModel, create_engine

from .config import plugin_config

engine = create_engine(plugin_config.database_url, echo=True)


@get_driver().on_startup
def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
