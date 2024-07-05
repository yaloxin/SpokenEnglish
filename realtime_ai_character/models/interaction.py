import datetime

from sqlalchemy import Column, DateTime, Integer, JSON, String, Unicode
from sqlalchemy.inspection import inspect

from realtime_ai_character.database.base import Base


class Interaction(Base):
    __tablename__ = "interactions"
    '''
    id：交互的唯一标识符，作为主键(primary key)。
    client_id：客户端 ID，已弃用(deprecated)，应使用 user_id 替代。
    user_id：用户 ID。
    session_id：会话 ID。
    client_message：客户端消息，已弃用(deprecated)，应使用 client_message_unicode 替代。
    server_message：服务器消息，已弃用(deprecated)，应使用 server_message_unicode 替代。
    client_message_unicode：客户端消息的 Unicode 格式。
    server_message_unicode：服务器消息的 Unicode 格式。
    timestamp：时间戳，记录交互发生的时间。
    platform：平台，指示交互发生的平台。
    action_type：动作类型，指示交互的类型。
    character_id：角色 ID，与交互相关联的角色的标识符。
    tools：工具，与交互相关的工具。
    language：语言，指示交互所使用的语言。
    message_id：消息 ID。
    llm_config：LLM 配置，LLM（Language Model）的配置信息。
    '''
    id = Column(Integer, primary_key=True, index=True, nullable=False)
    client_id = Column(Integer)  # deprecated, use user_id instead
    user_id = Column(String(50))
    session_id = Column(String(50))
    # deprecated, use client_message_unicode instead
    client_message = Column(String)
    # deprecated, use server_message_unicode instead
    server_message = Column(String)
    client_message_unicode = Column(Unicode(65535))
    server_message_unicode = Column(Unicode(65535))

    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    platform = Column(String(50))
    action_type = Column(String(50))
    character_id = Column(String(100))
    tools = Column(String(100))
    language = Column(String(10))
    message_id = Column(String(64))
    llm_config = Column(JSON())

    def to_dict(self):
        return {
            c.key: getattr(self, c.key).isoformat()
            if isinstance(getattr(self, c.key), datetime.datetime)
            else getattr(self, c.key)
            for c in inspect(self).mapper.column_attrs
        }

    def save(self, db):
        db.add(self)
        db.commit()
