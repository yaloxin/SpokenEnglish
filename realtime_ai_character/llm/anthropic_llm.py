from typing import Optional

from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chat_models import ChatAnthropic
from langchain.schema import BaseMessage, HumanMessage

from realtime_ai_character.database.chroma import get_chroma
from realtime_ai_character.llm.base import AsyncCallbackAudioHandler, AsyncCallbackTextHandler, LLM
from realtime_ai_character.logger import get_logger
from realtime_ai_character.utils import Character, timed

'''
get_logger 是一个用于获取或创建日志记录器的函数，通常由日志库（如 logging 模块）提供。__name__ 是 Python 中的一个特殊变量，它指示当前模块的名称。

当直接执行一个 Python 脚本时，__name__ 的值为 "__main__"。
当一个 Python 脚本被导入为模块时，__name__ 的值为该模块的名称。
'''
logger = get_logger(__name__)
'''
AnthropicLlm 类继承自 LLM 类，表示这是一个特定类型的语言模型。
在 __init__ 构造函数中，初始化了 AnthropicLlm 类的实例。它包括：
chat_anthropic: 使用 ChatAnthropic 类创建了一个聊天模型实例，传入了 model_name、temperature 和 streaming 参数。
config: 设置了模型的配置信息，包括 model、temperature 和 streaming 的值。
db: 使用 get_chroma() 函数获取了一个数据库对象，用于后续操作。
'''

class AnthropicLlm(LLM):
    def __init__(self, model):
        self.chat_anthropic = ChatAnthropic(model_name=model, temperature=0.5, streaming=True)
        self.config = {"model": model, "temperature": 0.5, "streaming": True}
        self.db = get_chroma()
    '''
    get_config 方法用于返回当前模型的配置信息。
    '''
    def get_config(self):
        return self.config
    '''
    achat 方法是一个异步方法，用于进行模型的对话生成。
    参数说明：
history: 用于存储对话历史的消息列表。
user_input: 用户的输入文本。
user_id: 用户的唯一标识符。
character: 代表聊天角色的 Character 对象。
callback: 文本处理器回调函数，用于处理生成的文本。
audioCallback: （可选）音频处理器回调函数，用于处理生成的音频。
metadata: （可选）元数据，用于传递附加信息。
*args, **kwargs: 可变位置参数和关键字参数，用于接收任意数量的额外参数。
    '''
    @timed
    async def achat(
        self,
        history: list[BaseMessage],
        user_input: str,
        user_id: str,
        character: Character,
        callback: AsyncCallbackTextHandler,
        audioCallback: Optional[AsyncCallbackAudioHandler] = None,
        metadata: Optional[dict] = None,
        *args,
        **kwargs,
    ) -> str:
        # 1. Generate context
        '''生成对话的上下文信息（调用 _generate_context 方法）。'''
        context = self._generate_context(user_input, character)

        # 2. Add user input to history
        '''
        将用户输入添加到对话历史中，并生成人类可读的消息对象。
        '''
        history.append(
            HumanMessage(
                content=character.llm_user_prompt.format(context=context, query=user_input)
            )
        )

        # 3. Generate response
        '''
        使用 chat_anthropic 聊天模型的 agenerate 方法生成响应，传入历史消息列表和回调函数列表。
        '''
        callbacks = [callback, StreamingStdOutCallbackHandler()]
        if audioCallback is not None:
            callbacks.append(audioCallback)
        response = await self.chat_anthropic.agenerate(
            [history], callbacks=callbacks, metadata=metadata
        )
        '''
        记录生成的响应日志，并返回生成的文本结果。
        '''
        logger.info(f"Response: {response}")
        return response.generations[0][0].text
    '''
    _generate_context 方法用于根据用户输入文本查询数据库，并生成用于模型对话的上下文信息。
    '''
    def _generate_context(self, query, character: Character) -> str:
        docs = self.db.similarity_search(query)
        docs = [d for d in docs if d.metadata["character_name"] == character.name]
        logger.info(f"Found {len(docs)} documents")

        context = "\n".join([d.page_content for d in docs])
        return context
