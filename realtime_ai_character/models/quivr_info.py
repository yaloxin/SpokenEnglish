from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, Integer, String

from realtime_ai_character.database.base import Base


class QuivrInfo(Base):
    __tablename__ = "quivr_info"
    '''
    列（columns）包括：
id：自增的整数型主键。
user_id：用户 ID。
quivr_api_key：Quivr API 密钥。
quivr_brain_id：Quivr 的大脑 ID。'''
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50))
    quivr_api_key = Column(String)
    quivr_brain_id = Column(String)

    def save(self, db):
        db.add(self)
        db.commit()


class UpdateQuivrInfoRequest(BaseModel):
    quivr_api_key: Optional[str] = None
    quivr_brain_id: Optional[str] = None
