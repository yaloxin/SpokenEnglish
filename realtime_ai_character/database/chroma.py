import os
from dotenv import load_dotenv

from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma

from realtime_ai_character.logger import get_logger

# load_dotenv()函数来加载环境变量，这个函数通常用于从.env文件中加载环境变量。
load_dotenv()
# 获取了一个日志记录器对象，并将其赋值给logger变量。
logger = get_logger(__name__)


def get_chroma(embedding: bool = True):
    if embedding:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise Exception("OPENAI_API_KEY is required to generate embeddings")
        if os.getenv("OPENAI_API_TYPE") == "azure":
            embedding_function = OpenAIEmbeddings(
                openai_api_key=openai_api_key,
                deployment=os.getenv(
                    "OPENAI_API_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-ada-002"
                ),
                chunk_size=1,
            )
        else:
            embedding_function = OpenAIEmbeddings(openai_api_key=openai_api_key)
    else:
        embedding_function = None

    chroma = Chroma(
        collection_name="llm",
        embedding_function=embedding_function,
        persist_directory="./chroma.db",
    )
    return chroma
