import os
from ollama import Client

with open(r"main_server\utils\README.md", "r", encoding="utf-8") as f:
    system_prompt = f.read()

print(os.environ.get('OLLAMA_API_KEY'))
client = Client(
    host="https://ollama.com",
    headers={'Authorization': 'Bearer ' + "32ff10c1ae7147eebde0190d1bc82b09.JrP5ZoiSnJQzfwdl4Pxh8ieA"}
)

messages = [
    {'role': 'user', 'content': 'hi'}
]

print(client.chat('gpt-oss:20b-cloud', messages=messages, stream=False)['message']['content'])
