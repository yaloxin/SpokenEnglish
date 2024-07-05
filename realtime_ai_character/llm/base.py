import asyncio
import re
from abc import ABC, abstractmethod
from typing import Callable, Coroutine, Optional

import emoji
from fastapi import WebSocket
from langchain.callbacks.base import AsyncCallbackHandler
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.schema.messages import BaseMessage

from realtime_ai_character.audio.text_to_speech.base import TextToSpeech
from realtime_ai_character.logger import get_logger
from realtime_ai_character.utils import Character, get_timer, timed


logger = get_logger(__name__)

timer = get_timer()

StreamingStdOutCallbackHandler.on_chat_model_start = lambda *args, **kwargs: None


class AsyncCallbackTextHandler(AsyncCallbackHandler):
    def __init__(
        self,
            # 用于处理新令牌的回调函数，是一个异步可调用对象，接受一个字符串参数。
        on_new_token: Callable[[str], Coroutine],
            # 储存
        token_buffer: list[str],
            # 处理LLM结束时的回调函数
        on_llm_end: Callable[[str], Coroutine],
            # 可选。用于控制文本到语音转换（TTS）的事件。
        tts_event: Optional[asyncio.Event] = None,
        *args,
        **kwargs
    ):
        # 调用了父类AsyncCallbackHandler的构造函数
        super().__init__(*args, **kwargs)
        # 类的初始化
        self.on_new_token = on_new_token
        self._on_llm_end = on_llm_end
        self.token_buffer = token_buffer
        self.tts_event = tts_event

    # on_chat_model_start和on_llm_new_token是两个异步方法，它们都被定义为占位符，不执行任何操作。
    # 这些方法可能在子类中被重写以提供具体的行为。
    async def on_chat_model_start(self, *args, **kwargs):
        pass

    async def on_llm_new_token(self, token: str, *args, **kwargs):
        if self.token_buffer is not None:
            self.token_buffer.append(token)
        if self.tts_event is not None:
            while not self.tts_event.is_set():
                await asyncio.sleep(0.01)
                await self.on_new_token(token)
        else:
            await self.on_new_token(token)
    ''' 
    当LLM结束时调用
    如果定义了_on_llm_end回调函数，则调用该函数，并传递已收集的令牌。
    清空token_buffer列表。
    '''
    async def on_llm_end(self, *args, **kwargs):
        if self._on_llm_end is not None:
            await self._on_llm_end("".join(self.token_buffer))
            self.token_buffer.clear()


class AsyncCallbackAudioHandler(AsyncCallbackHandler):
    def __init__(
        self,
        text_to_speech: TextToSpeech,
            # 用于与客户端通信的WebSocket对象
        websocket: WebSocket,
            # 用于控制文本到语音转换的事件。
        tts_event: asyncio.Event,
            # 指定要使用的语音的ID
        voice_id: str = "",
            # 指定要使用的语言。
        language: str = "en-US",
            # 用于指定Twilio流ID。
        sid: str = "",
            # 指定平台信息。
        platform: str = "",

        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.text_to_speech = text_to_speech
        self.websocket = websocket
        self.current_sentence = ""
        self.voice_id = voice_id
        self.language = language
        self.is_reply = False  # the start of the reply. i.e. the substring after '>'
        self.tts_event = tts_event
        self.twilio_stream_id = sid
        self.platform = platform
        # optimization: trade off between latency and quality for the first sentence
        # 初始化为0，用于跟踪句子的索引
        self.sentence_idx = 0

    # 它们都被定义为占位符，不执行任何操作。
    async def on_chat_model_start(self, *args, **kwargs):
        pass

    async def on_llm_new_token(self, token: str, *args, **kwargs):
        timer.log("LLM First Token", lambda: timer.start("LLM First Sentence"))
        # skip emojis
        token = emoji.replace_emoji(token, "")
        token = self.text_regulator(token)
        if not token:
            return
        for char in token:
            await self._on_llm_new_character(char)
    '''
    用于处理LLM生成的新字符。它执行以下操作：
    将新字符添加到当前句子中。
    如果遇到标点符号或换行符，将当前句子发送给文本到语音转换模块，并重置当前句子。
    '''
    async def _on_llm_new_character(self, char: str):
        # send to TTS in sentences
        punctuation = False
        if (
            # English punctuations
            (
                char == " "
                and self.current_sentence != ""
                and self.current_sentence[-1] in {".", "?", "!"}
            )
            # Chinese/Japanese/Korean punctuations
            or (char in {"。", "？", "！"})
            # newline
            or (char in {"\n", "\r", "\t"})
        ):
            punctuation = True

        self.current_sentence += char

        if punctuation and self.current_sentence.strip():
            first_sentence = self.sentence_idx == 0
            if first_sentence:
                timer.log("LLM First Sentence", lambda: timer.start("TTS First Sentence"))
            await self.text_to_speech.stream(
                text=self.current_sentence.strip(),
                websocket=self.websocket,
                tts_event=self.tts_event,
                voice_id=self.voice_id,
                first_sentence=first_sentence,
                language=self.language,
                sid=self.twilio_stream_id,
                platform=self.platform,
                priority=self.sentence_idx,
            )
            self.current_sentence = ""
            timer.log("TTS First Sentence")
            self.sentence_idx += 1

    # 另一个异步方法，当LLM结束时调用。它执行以下操作：
    # 如果当前句子不为空，则将其发送给文本到语音转换模块。
    async def on_llm_end(self, *args, **kwargs):
        first_sentence = self.sentence_idx == 0
        if self.current_sentence.strip():
            await self.text_to_speech.stream(
                text=self.current_sentence.strip(),
                websocket=self.websocket,
                tts_event=self.tts_event,
                voice_id=self.voice_id,
                first_sentence=first_sentence,
                language=self.language,
                priority=self.sentence_idx,
            )

    def text_regulator(self, text):
        pattern = (
            r"[\u200B\u200C\u200D\u200E\u200F\uFEFF\u00AD\u2060\uFFFC\uFFFD]"  # Format characters
            r"|[\uFE00-\uFE0F]"  # Variation selectors
            r"|[\uE000-\uF8FF]"  # Private use area
            r"|[\uFFF0-\uFFFF]"  # Specials
        )
        filtered_text = re.sub(pattern, "", text)
        return filtered_text


class LLM(ABC):
    @abstractmethod
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
        **kwargs
    ):
        pass

    @abstractmethod
    def get_config(self):
        pass
