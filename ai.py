import asyncio
from gigachat import GigaChat

SYSTEM_PROMPT = """Ты — мастер интерактивной RPG. Ведёшь игрока по вымышленному миру.

СТРОГИЕ ЗАПРЕТЫ (нарушение = отказ):
- Не упоминай реальных политиков, партии, действующих государственных деятелей.
- Не описывай реальные политические события, выборы, протесты, военные конфликты.
- Не пропагандируй наркотики, суицид, насилие, экстремизм, терроризм.
- Не генерируй инструкции по изготовлению оружия, взрывчатки, наркотиков.
- Не разжигай ненависть по признаку пола, расы, религии, национальности.
- Не пиши дезинформацию о реальных событиях.
- Если игрок просит запрещённое — вежливо откажись и переведи сюжет в безопасное русло.

Правила игры:
- Пиши ярко, коротко: 3-6 предложений.
- Заканчивай выбором или вопросом.
- Помни всё, что игрок делал раньше.
"""

BLOCKED_WORDS = [
    "наркотик", "героин", "кокаин", "мефедрон",
    "суицид", "самоубийств", "убить себя", "покончить с собой",
    "теракт", "взорвать", "бомба", "взрывчатк", "оружие массового",
    "экстремизм", "терроризм", "джихад",
    "политик", "путин", "навальн", "протест", "революция",
    "выборы", "референдум", "спецоперация", "война",
]

def is_blocked(text: str) -> bool:
    low = text.lower()
    return any(w in low for w in BLOCKED_WORDS)

_client = None

def _get_client(credentials):
    global _client
    if _client is None:
        _client = GigaChat(
            credentials=credentials,
            verify_ssl_certs=False,
            scope="GIGACHAT_API_PERS",  # для физлиц
        )
    return _client

async def generate(credentials, story, user_action):
    if is_blocked(user_action):
        return ("🚫 Этот запрос нарушает правила игры. Я могу вести только "
                "безопасные сюжеты. Попробуй другое действие — например, "
                "«осматриваюсь» или «иду в лес».")

    client = _get_client(credentials)
    context = f"ПРЕДЫДУЩАЯ ИСТОРИЯ:\n{story}\n\nИГРОК: {user_action}\n\nМАСТЕР:"

    def _sync_generate():
        response = client.chat({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context}
            ],
            "temperature": 0.7,
            "max_tokens": 400,
        })
        return response.choices[0].message.content

    try:
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, _sync_generate)
    except Exception as e:
        return f"⚠️ Ошибка ИИ: {str(e)[:100]}. Попробуй ещё раз."

    if is_blocked(text):
        return ("🚫 Сюжет ушёл в недопустимую тему. Давай вернёмся в безопасное "
                "русло. Опиши, что делает герой.")

    return text