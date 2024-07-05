from typing import Optional
import requests
import json
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.schema import BaseMessage, HumanMessage
from realtime_ai_character.database.chroma import get_chroma
from realtime_ai_character.llm.base import (
    AsyncCallbackAudioHandler,
    AsyncCallbackTextHandler,
    LLM,
)
from realtime_ai_character.logger import get_logger
from realtime_ai_character.utils import Character, timed

logger = get_logger(__name__)

class LocalLlm(LLM):
    def __init__(self, url):
        self.api_base_url = url
        self.config = {"model": "llama3", "temperature": 0.5, "streaming": True}
        self.db = get_chroma()

    def get_config(self):
        return self.config

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
        context = self._generate_context(user_input, character)

        # 2. Add user input to history
        history.append(
            HumanMessage(
                content=character.llm_user_prompt.format(context=context, query=user_input)
            )
        )

        # 3. Generate response using llama3
        response = self.send_message_to_ollama(user_input)
        logger.info(f"Response: {response}")
        await callback(response)  # Sending response to callback
        if audioCallback is not None:
            await audioCallback(response)
        return response

    def _generate_context(self, query, character: Character) -> str:
        docs = self.db.similarity_search(query)
        docs = [d for d in docs if d.metadata["character_name"] == character.name]
        logger.info(f"Found {len(docs)} documents")

        context = "\n".join([d.page_content for d in docs])
        return context

    def send_message_to_ollama(self, message: str, port=11434) -> str:
        url = f"http://localhost:{port}/api/generate"
        payload = {
            "model": "llama3",
            "prompt": message
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            response_content = ""
            for line in response.iter_lines():
                if line:
                    response_content += json.loads(line)["response"]
            return response_content
        else:
            return f"Error: {response.status_code} - {response.text}"
