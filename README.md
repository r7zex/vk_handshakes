# VK Handshakes App
Локальный сервис для поиска кратчайшей цепочки
«рукопожатий» между двумя пользователями ВКонтакте.

## Возможности

- Узнать кол-во рукопожатий до любого человека
- Не учитывать прямую дружбу
- Гибко настраивать макс кол-во искомых рукопожатиий и макс кол-во друзей у искомых рукопожатий
- Кэшировать поиски ранее
- Не учитывать определённых людей при поиске рукопожатий
  
## Запуск

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Настройки

Базовые настройки лежат в `app/config.py`.

По умолчанию используется:

```text
API_BASE_URL = https://vkresult.ru/method
API_VERSION = 5.124
MAX_DEPTH = 11
MAX_FRIENDS_PER_USER = 250
MAX_ROOT_FRIENDS = 5000
API_DELAY = 0.34
```

Пользовательские настройки сохраняются в `%APPDATA%/VKHandshakes/settings.json`.
Кэш хранится в `%APPDATA%/VKHandshakes/cache.sqlite`.
