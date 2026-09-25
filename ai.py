import asyncio
import time
import uuid
import aiohttp
import ssl

OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
SCOPE = "GIGACHAT_API_PERS"

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

_token_cache = {"value": None, "expires_at": 0}

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def is_blocked(text: str) -> bool:
    low = text.lower()
    return any(w in low for w in BLOCKED_WORDS)


async def _get_token(auth_key: str) -> str:
    now = time.time()
    if _token_cache["value"] and _token_cache["expires_at"] > now:
        return _token_cache["value"]

    headers = {
        "Authorization": f"Basic {auth_key}",
        "RqUID": str(uuid.uuid4()),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    data = {"scope": SCOPE}

    async with aiohttp.ClientSession() as s:
        async with s.post(OAUTH_URL, headers=headers, data=data, ssl=_ssl_ctx) as r:
            result = await r.json()
            token = result.get("access_token")
            if not token:
                raise RuntimeError(f"GigaChat OAuth error: {result}")
            _token_cache["value"] = token
            _token_cache["expires_at"] = now + 25 * 60
            return token


async def generate(auth_key, story, user_action):
    if is_blocked(user_action):
        return ("🚫 Этот запрос нарушает правила игры. Я могу вести только "
                "безопасные сюжеты. Попробуй другое действие — например, "
                "«осматриваюсь» или «иду в лес».")

    try:
        token = await _get_token(auth_key)
    except Exception as e:
        print(f"Token error: {e}")
        return "⚠️ Не удалось авторизоваться в GigaChat. Попробуй позже."

    context = f"ПРЕДЫДУЩАЯ ИСТОРИЯ:\n{story}\n\nИГРОК: {user_action}\n\nМАСТЕР:"
    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
        "temperature": 0.7,
        "max_tokens": 400,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    async with aiohttp.ClientSession() as s:
        async with s.post(API_URL, json=payload, headers=headers, ssl=_ssl_ctx) as r:
            data = await r.json()
            try:
                text = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError):
                print(f"GigaChat response error: {data}")
                return "⚠️ ИИ задумался. Попробуй ещё раз."

    if is_blocked(text):
        return ("🚫 Сюжет ушёл в недопустимую тему. Давай вернёмся в безопасное "
                "русло. Опиши, что делает герой.")

    return text