"""map target

Revision ID: 09b1ff566d51
Revises: 82ec0729d48a
Create Date: 2023-09-19 10:42:52.402886

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

# revision identifiers, used by Alembic.
revision = "09b1ff566d51"
down_revision = "82ec0729d48a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base = automap_base()
    Base.prepare(op.get_bind())
    MorningGreeting = Base.classes.morning_greeting_morninggreeting
    with Session(op.get_bind()) as session:
        mornings = session.scalars(sa.select(MorningGreeting)).all()
        for morning in mornings:
            if morning.platform == "qq":
                morning.target = {
                    "platform_type": "QQ Group",
                    "group_id": int(morning.group_id),
                }
            elif morning.platform == "qqguild":
                morning.target = {
                    "platform_type": "QQ Guild Channel",
                    "channel_id": int(morning.channel_id),
                }
            elif morning.platform == "kaiheila":
                morning.target = {
                    "platform_type": "Kaiheila Channel",
                    "channel_id": morning.channel_id,
                }
            elif morning.platform == "telegram":
                if morning.channel_id == "":
                    morning.target = {
                        "platform_type": "Telegram Common",
                        "chat_id": morning.group_id,
                    }
                else:
                    morning.target = {
                        "platform_type": "Telegram Forum",
                        "chat_id": int(morning.guild_id),
                        "message_thread_id": int(morning.channel_id),
                    }
            elif morning.platform == "feishu":
                morning.target = {
                    "platform_type": "Feishu Group",
                    "chat_id": morning.group_id,
                }
            else:
                morning.target = {
                    "platform_type": "Unknow Onebot 12 Platform",
                    "platform": morning.platform,
                    "detail_type": "group" if morning.group_id else "channel",
                    "group_id": morning.group_id,
                    "guild_id": morning.guild_id,
                    "channel_id": morning.channel_id,
                }

        session.add_all(mornings)
        session.commit()


def downgrade() -> None:
    Base = automap_base()
    Base.prepare(op.get_bind())
    MorningGreeting = Base.classes.morning_greeting_morninggreeting
    with Session(op.get_bind()) as session:
        mornings = session.scalars(sa.select(MorningGreeting)).all()
        for morning in mornings:
            platform_type = morning.target["platform_type"]
            if platform_type == "QQ Group":
                morning.group_id = str(morning.target["group_id"])
            elif platform_type == "QQ Guild Channel":
                morning.channel_id = str(morning.target["channel_id"])
            elif platform_type == "Kaiheila Channel":
                morning.channel_id = morning.target["channel_id"]
            elif platform_type == "Telegram Common":
                morning.group_id = str(morning.target["chat_id"])
                morning.channel_id = None
            elif platform_type == "Telegram Forum":
                morning.guild_id = str(morning.target["chat_id"])
                morning.channel_id = str(morning.target["message_thread_id"])
            elif platform_type == "Feishu Group":
                morning.group_id = morning.target["chat_id"]
            else:
                morning.platform = morning.target["platform"]
                morning.group_id = morning.target["group_id"]
                morning.guild_id = morning.target["guild_id"]
                morning.channel_id = morning.target["channel_id"]

        session.add_all(mornings)
        session.commit()
