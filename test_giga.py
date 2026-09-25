from gigachat import GigaChat
from config import GIGACHAT_CREDENTIALS, GIGACHAT_SCOPE

client = GigaChat(
    credentials=GIGACHAT_CREDENTIALS,
    scope=GIGACHAT_SCOPE,
    model="GigaChat-2",          # ← добавили модель
    verify_ssl_certs=False,
)

response = client.chat("Привет! Опиши коротко подземелье для RPG.")
print(response.choices[0].message.content)