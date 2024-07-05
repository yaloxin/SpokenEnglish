import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, String, Unicode
from sqlalchemy.inspection import inspect

from realtime_ai_character.database.base import Base


class Feedback(Base):
    '''
    这个模型代表了数据库中的 feedbacks 表格
    '''
    __tablename__ = "feedbacks"
    '''
    message_id：消息的唯一标识符，作为主键(primary key)。
    session_id：会话的标识符，可选。
    user_id：用户的标识符，可选。
    server_message_unicode：服务器消息的 Unicode 格式，可选。
    feedback：反馈信息，可选。
    comment：评论，可选。
    created_at：记录创建时间的日期时间字段。
    '''

    message_id = Column(String(64), primary_key=True)
    session_id = Column(String(50), nullable=True)
    user_id = Column(String(50), nullable=True)
    server_message_unicode = Column(Unicode(65535), nullable=True)
    feedback = Column(String(100), nullable=True)
    comment = Column(Unicode(65535), nullable=True)
    created_at = Column(DateTime(), nullable=False)
    '''将模型实例转换为字典格式，方便序列化为
    JSON对象。'''
    def to_dict(self):
        return {
            c.key: getattr(self, c.key).isoformat()
            if isinstance(getattr(self, c.key), datetime.datetime)
            else getattr(self, c.key)
            for c in inspect(self).mapper.column_attrs
        }
    '''将模型实例保存到数据库中。'''
    def save(self, db):
        db.add(self)
        db.commit()

'''
FeedbackRequest 是用于处理反馈信息的请求模型，包括消息 ID、会话 ID、服务器消息 Unicode 格式、反馈信息和评论。
'''
class FeedbackRequest(BaseModel):
    message_id: str
    session_id: Optional[str] = None
    server_message_unicode: Optional[str] = None
    feedback: Optional[str] = None
    comment: Optional[str] = None
