from transformers import AutoTokenizer, AutoModelForCausalLM
import os


proxy_server = '127.0.0.1'
proxy_port = '7890'

# 设置环境变量
os.environ['http_proxy'] = f'http://{proxy_server}:{proxy_port}'
os.environ['https_proxy'] = f'http://{proxy_server}:{proxy_port}'

huggingface_token = "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"
tokenizer = AutoTokenizer.from_pretrained("google/gemma-2b", use_auth_token=huggingface_token)

model = AutoModelForCausalLM.from_pretrained("google/gemma-2b", use_auth_token=huggingface_token)
input_text = "What do you think are the benefits of AI for your life right now?"
input_ids = tokenizer(input_text, return_tensors="pt")

outputs = model.generate(**input_ids, max_length=200)
print(tokenizer.decode(outputs[0]))