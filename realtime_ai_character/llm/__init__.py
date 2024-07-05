# 导入模块和库

import os
# 从 functools 库中导入 cache 装饰器，用于缓存函数的返回值，提高函数调用的性能。
from functools import cache
# 从 dotenv 库中导入 load_dotenv 函数，用于从 .env 文件中加载环境变量。
from dotenv import load_dotenv
# 导入 BaseChatModel 类
from langchain.chat_models.base import BaseChatModel
# 导入 LLM 类。
from realtime_ai_character.llm.base import LLM


# 加载 .env 文件中的环境变量，以便后续代码中可以使用 os.getenv() 获取这些环境变量的值。
load_dotenv()


def get_llm(model="gpt-3.5-turbo-16k") -> LLM:
    # model = "gpt-3.5-turbo-16k"：这是函数的参数
    # model的默认值，如果调用函数时未提供model参数，则默认使用
    # "gpt-3.5-turbo-16k"。
    model = os.getenv("LLM_MODEL_USE", model)
    '''os.getenv("LLM_MODEL_USE", model)：这里使用
    os.getenv
    函数从环境变量中获取名为
    "LLM_MODEL_USE"的值，如果环境变量中没有设置，则使用
    model
    参数的默认值。'''

    '''
    如果 model 以 "gpt" 开头：
导入 realtime_ai_character.llm.openai_llm.OpenaiLlm 类。
创建并返回一个 OpenaiLlm 对象，传入 model 参数作为构造函数的参数。
如果 model 以 "claude" 开头：
导入 realtime_ai_character.llm.anthropic_llm.AnthropicLlm 类。
创建并返回一个 AnthropicLlm 对象，传入 model 参数作为构造函数的参数。
如果 model 中包含 "localhost"：
获取环境变量 "LOCAL_LLM_URL" 的值作为 local_llm_url。
如果 local_llm_url 不为空：
导入 realtime_ai_character.llm.local_llm.LocalLlm 类。
创建并返回一个 LocalLlm 对象，传入 url=local_llm_url 作为构造函数的参数。
如果 local_llm_url 为空，则抛出 ValueError 异常，提示 "LOCAL_LLM_URL not set"。
如果 model 中包含 "llama"：
导入 realtime_ai_character.llm.anyscale_llm.AnysacleLlm 类。
创建并返回一个 AnysacleLlm 对象，传入 model 参数作为构造函数的参数。
如果 model 中包含 "rebyte"：
导入 realtime_ai_character.llm.rebyte_llm.RebyteLlm 类。
创建并返回一个 RebyteLlm 对象。
如果以上所有条件都不满足，则抛出 ValueError 异常，提示 "Invalid llm model: {model}"
    '''
    if model.startswith("gpt"):
        from realtime_ai_character.llm.openai_llm import OpenaiLlm

        return OpenaiLlm(model=model)
    elif model.startswith("claude"):
        from realtime_ai_character.llm.anthropic_llm import AnthropicLlm

        return AnthropicLlm(model=model)
    elif "localhost" in model:
        # Currently use llama2-wrapper to run local llama models
        local_llm_url = os.getenv("LOCAL_LLM_URL", "")
        if local_llm_url:
            from realtime_ai_character.llm.local_llm import LocalLlm

            return LocalLlm(url=local_llm_url)
        else:
            raise ValueError("LOCAL_LLM_URL not set")
    elif "llama" in model:
        # Currently use Anyscale to support llama models
        from realtime_ai_character.llm.anyscale_llm import AnysacleLlm

        return AnysacleLlm(model=model)
    elif "rebyte" in model:
        from realtime_ai_character.llm.rebyte_llm import RebyteLlm

        return RebyteLlm()
    elif "LLAMA_MODEL" in model:
        from realtime_ai_character.llm.llama_llm import LlamaLlm

        return LlamaLlm()
    else:
        raise ValueError(f"Invalid llm model: {model}")

'''
-> BaseChatModel：这是函数的类型提示（type hint），表示函数将返回一个 BaseChatModel 类型的对象或接口。
'''
def get_chat_model(model="gpt-3.5-turbo-16k") -> BaseChatModel:
    '''
    这里使用 os.getenv 函数从环境变量中获取名为 "LLM_MODEL_USE" 的值，
    如果环境变量中没有设置，则使用 model 参数的默认值。
    '''
    model = os.getenv("LLM_MODEL_USE", model)

    """
    如果 model 以 "gpt" 开头：
导入 realtime_ai_character.llm.openai_llm.OpenaiLlm 类。
创建 OpenaiLlm 对象并返回其 chat_open_ai 属性。
如果 model 以 "claude" 开头：
导入 realtime_ai_character.llm.anthropic_llm.AnthropicLlm 类。
创建 AnthropicLlm 对象并返回其 chat_anthropic 属性。
如果 model 中包含 "localhost"：
获取环境变量 "LOCAL_LLM_URL" 的值作为 local_llm_url。
如果 local_llm_url 不为空：
导入 realtime_ai_character.llm.local_llm.LocalLlm 类。
创建 LocalLlm 对象并返回其 chat_open_ai 属性。
如果 local_llm_url 为空，则抛出 ValueError 异常，提示 "LOCAL_LLM_URL not set"。
如果 model 中包含 "llama"：
导入 realtime_ai_character.llm.anyscale_llm.AnysacleLlm 类。
创建 AnysacleLlm 对象并返回其 chat_open_ai 属性。
如果 model 中包含 "rebyte"：
导入 realtime_ai_character.llm.rebyte_llm.RebyteLlm 类。
创建 RebyteLlm 对象并返回其 chat_rebyte 属性。
如果以上所有条件都不满足，则抛出 ValueError 异常，提示 "Invalid llm model: {model}"。
    """
    if model.startswith("gpt"):
        from realtime_ai_character.llm.openai_llm import OpenaiLlm

        return OpenaiLlm(model=model).chat_open_ai
    elif model.startswith("claude"):
        from realtime_ai_character.llm.anthropic_llm import AnthropicLlm

        return AnthropicLlm(model=model).chat_anthropic
    elif "localhost" in model:
        # Currently use llama2-wrapper to run local llama models
        local_llm_url = os.getenv("LOCAL_LLM_URL", "")
        if local_llm_url:
            from realtime_ai_character.llm.local_llm import LocalLlm

            return LocalLlm(url=local_llm_url).chat_open_ai
        else:
            raise ValueError("LOCAL_LLM_URL not set")
    elif "llama" in model:
        # Currently use Anyscale to support llama models
        from realtime_ai_character.llm.anyscale_llm import AnysacleLlm

        return AnysacleLlm(model=model).chat_open_ai
    elif "rebyte" in model:
        from realtime_ai_character.llm.rebyte_llm import RebyteLlm

        return RebyteLlm().chat_rebyte
    else:
        raise ValueError(f"Invalid llm model: {model}")

'''@cache 装饰器修饰的函数'''
@cache
def get_chat_model_from_env() -> BaseChatModel:
    """GPT-4 has the best performance while generating system prompt."""
    """
    这部分代码根据不同的环境变量来决定调用 get_chat_model 函数获取哪种聊天模型的接口或对象。
    如果环境变量 "REBYTE_API_KEY" 存在，则调用 get_chat_model(model="rebyte") 返回 Rebyte 模型的聊天接口。
    如果环境变量 "OPENAI_API_KEY" 存在，则调用 get_chat_model(model="gpt-4") 返回 GPT-4 模型的聊天接口。
    如果环境变量 "ANTHROPIC_API_KEY" 存在，则调用 get_chat_model(model="claude-2") 返回 Claude-2 模型的聊天接口。
    如果环境变量 "ANYSCALE_API_KEY" 存在，则调用 get_chat_model(model="meta-llama/Llama-2-70b-chat-hf") 返回 AnyScale 模型的聊天接口。
    如果环境变量 "LOCAL_LLM_URL" 存在，则调用 get_chat_model(model="localhost") 返回本地 LLM 模型的聊天接口。
    如果以上所有条件都不满足（即没有找到任何 llm 的 api key），则抛出 ValueError 异常，提示 "No llm api key found in env"。
    """
    if os.getenv("REBYTE_API_KEY"):
        return get_chat_model(model="rebyte")
    elif os.getenv("OPENAI_API_KEY"):
        return get_chat_model(model="gpt-4")
    elif os.getenv("ANTHROPIC_API_KEY"):
        return get_chat_model(model="claude-2")
    elif os.getenv("ANYSCALE_API_KEY"):
        return get_chat_model(model="meta-llama/Llama-2-70b-chat-hf")
    elif os.getenv("LOCAL_LLM_URL"):
        return get_chat_model(model="localhost")

    raise ValueError("No llm api key found in env")
