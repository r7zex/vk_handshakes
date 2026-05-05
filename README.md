# VK Handshakes App

Локальное desktop-приложение на Python/PySide6 для поиска кратчайшей цепочки
«рукопожатий» между двумя пользователями ВКонтакте.

## Возможности

- тёмный PySide6-интерфейс;
- ручная вставка VK `access_token` или OAuth-ссылки с `access_token=...`;
- локальное хранение токена через `keyring` с fallback в файл;
- автоматическая проверка токена через `users.get`;
- поддержка ввода `vk.com/name`, `https://vk.com/name`, `id123` и `123`;
- поиск через двунаправленный BFS;
- запрос друзей через `execute` с fallback на прямой `friends.get`;
- JSONP-парсинг для `https://vkresult.ru/method`;
- фильтрация закрытых/удалённых профилей через batch `users.get`;
- отсечение хабов;
- SQLite-кэш пользователей, друзей, профилей и хабов;
- прогресс поиска, отмена, вывод результата ссылками, экспорт TXT/JSON.

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

## Безопасность токена

Приложение не выводит полный `access_token` в UI или лог. Для отображения
используется маска вида `vk2.a.ab...wxyz`.
