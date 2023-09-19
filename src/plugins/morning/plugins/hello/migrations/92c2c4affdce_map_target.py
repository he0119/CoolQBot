"""map target

Revision ID: 92c2c4affdce
Revises: 169da32b92d8
Create Date: 2023-09-19 10:43:15.269932

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

# revision identifiers, used by Alembic.
revision = "92c2c4affdce"
down_revision = "169da32b92d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base = automap_base()
    Base.prepare(op.get_bind())
    Hello = Base.classes.hello_hello
    with Session(op.get_bind()) as session:
        hellos = session.scalars(sa.select(Hello)).all()
        for hello in hellos:
            if hello.platform == "qq":
                hello.target = {
                    "platform_type": "QQ Group",
                    "group_id": int(hello.group_id),
                }
            elif hello.platform == "qqguild":
                hello.target = {
                    "platform_type": "QQ Guild Channel",
                    "channel_id": int(hello.channel_id),
                }
            elif hello.platform == "kaiheila":
                hello.target = {
                    "platform_type": "Kaiheila Channel",
                    "channel_id": hello.channel_id,
                }
            elif hello.platform == "telegram":
                if hello.channel_id == "":
                    hello.target = {
                        "platform_type": "Telegram Common",
                        "chat_id": hello.group_id,
                    }
                else:
                    hello.target = {
                        "platform_type": "Telegram Forum",
                        "chat_id": int(hello.guild_id),
                        "message_thread_id": int(hello.channel_id),
                    }
            elif hello.platform == "feishu":
                hello.target = {
                    "platform_type": "Feishu Group",
                    "chat_id": hello.group_id,
                }
            else:
                hello.target = {
                    "platform_type": "Unknow Onebot 12 Platform",
                    "platform": hello.platform,
                    "detail_type": "group" if hello.group_id else "channel",
                    "group_id": hello.group_id,
                    "guild_id": hello.guild_id,
                    "channel_id": hello.channel_id,
                }

        session.add_all(hellos)
        session.commit()


def downgrade() -> None:
    Base = automap_base()
    Base.prepare(op.get_bind())
    Hello = Base.classes.hello_hello
    with Session(op.get_bind()) as session:
        hellos = session.scalars(sa.select(Hello)).all()
        for hello in hellos:
            platform_type = hello.target["platform_type"]
            if platform_type == "QQ Group":
                hello.group_id = str(hello.target["group_id"])
            elif platform_type == "QQ Guild Channel":
                hello.channel_id = str(hello.target["channel_id"])
            elif platform_type == "Kaiheila Channel":
                hello.channel_id = hello.target["channel_id"]
            elif platform_type == "Telegram Common":
                hello.group_id = str(hello.target["chat_id"])
                hello.channel_id = None
            elif platform_type == "Telegram Forum":
                hello.guild_id = str(hello.target["chat_id"])
                hello.channel_id = str(hello.target["message_thread_id"])
            elif platform_type == "Feishu Group":
                hello.group_id = hello.target["chat_id"]
            else:
                hello.platform = hello.target["platform"]
                hello.group_id = hello.target["group_id"]
                hello.guild_id = hello.target["guild_id"]
                hello.channel_id = hello.target["channel_id"]

        session.add_all(hellos)
        session.commit()
