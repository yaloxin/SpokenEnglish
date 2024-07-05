import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, JSON, String
from sqlalchemy.inspection import inspect

from realtime_ai_character.database.base import Base


class Character(Base):
    __tablename__ = "characters"
    '''
    这是一个 SQLAlchemy 模型，代表了数据库中的 characters 表格。它包含了一些列列（columns），每一列对应表格中的一个字段。这些字段包括：

id: 角色的唯一标识符，主键(primary key)。
name: 角色的名称。
system_prompt: 系统提示，可能是由系统自动生成的。
user_prompt: 用户提示，可能是用户提供的输入。
text_to_speech_use: 文字转语音使用情况。
voice_id: 语音的标识符。
author_id: 作者的标识符。
visibility: 可见性，指示角色是否可见。
data: 数据，一个 JSON 字段，可以存储各种额外的数据。
created_at 和 updated_at: 记录创建和更新时间的日期时间字段。
tts: 文字转语音（Text-To-Speech）相关的信息。
avatar_id: 头像的标识符。
background_text: 背景文本。
rebyte_api_project_id, rebyte_api_agent_id, rebyte_api_version: 与 rebyte API 相关的字段。
    '''
    id = Column(String(), primary_key=True, index=True, nullable=False)
    name = Column(String(1024), nullable=False)
    system_prompt = Column(String(262144), nullable=True)
    user_prompt = Column(String(262144), nullable=True)
    text_to_speech_use = Column(String(100), nullable=True)
    voice_id = Column(String(100), nullable=True)
    author_id = Column(String(100), nullable=True)
    visibility = Column(String(100), nullable=True)
    data = Column(JSON(), nullable=True)
    created_at = Column(DateTime(), nullable=False)
    updated_at = Column(DateTime(), nullable=False)
    tts = Column(String(64), nullable=True)
    avatar_id = Column(String(100), nullable=True)
    background_text = Column(String(262144), nullable=True)
    rebyte_api_project_id = Column(String(100), nullable=True)
    rebyte_api_agent_id = Column(String(100), nullable=True)
    rebyte_api_version = Column(Integer(), nullable=True)

    '''
    将模型实例转换为字典格式，方便序列化为 JSON 对象。
    '''
    def to_dict(self):
        return {
            c.key: getattr(self, c.key).isoformat()
            if isinstance(getattr(self, c.key), datetime.datetime)
            else getattr(self, c.key)
            for c in inspect(self).mapper.column_attrs
        }
    '''
    将模型实例保存到数据库中。
    '''
    def save(self, db):
        db.add(self)
        db.commit()

'''
CharacterRequest、EditCharacterRequest 和 DeleteCharacterRequest 是用于处理角色相关操作的请求模型，
包括创建、编辑和删除角色。
'''
class CharacterRequest(BaseModel):
    name: str
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    tts: Optional[str] = None
    voice_id: Optional[str] = None
    visibility: Optional[str] = None
    data: Optional[dict] = None
    avatar_id: Optional[str] = None
    background_text: Optional[str] = None
    rebyte_api_project_id: Optional[str] = None
    rebyte_api_agent_id: Optional[str] = None
    rebyte_api_version: Optional[int] = None


class EditCharacterRequest(BaseModel):
    id: str
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    tts: Optional[str] = None
    voice_id: Optional[str] = None
    visibility: Optional[str] = None
    data: Optional[dict] = None
    avatar_id: Optional[str] = None
    background_text: Optional[str] = None
    rebyte_api_project_id: Optional[str] = None
    rebyte_api_agent_id: Optional[str] = None
    rebyte_api_version: Optional[int] = None


class DeleteCharacterRequest(BaseModel):
    character_id: str

'''
GeneratePromptRequest 和 GenerateHighlightRequest 则用于生成提示和突出显示相关的请求。
'''
class GeneratePromptRequest(BaseModel):
    name: str
    background: Optional[str] = None


class GenerateHighlightRequest(BaseModel):
    context: str
    prompt: Optional[str] = None
