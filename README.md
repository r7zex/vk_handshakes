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

## TODO: автоматическое получение токена

Заготовка находится в `vk/barkov_token_flow.py`.

Заполнять нужно эти места:

1. `BarkovTokenAcquirer.acquire_token()` — общий сценарий браузера.
2. `open_friends_followers_section()` — выбор «Друзья и подписчики».
3. `open_collect_friends_followers_tool()` — выбор «Сбор друзей и подписчиков».
4. `login_with_vk()` — вход через VK и попытка взять `user_id` из OAuth redirect.
5. `fill_vk_profile()` — заполнение профиля для сбора.
6. `click_collect_button()` — кнопка «Собрать друзей и подписчиков страницы».
7. `wait_for_vkresult_request()` — ожидание network-запроса к `vkresult.ru/method/*`.
8. `extract_access_token_from_request()` — парсинг `access_token` из URL.

Статическая helper-страница для GitHub Pages лежит в `docs/auth-helper/`.
Она подготовлена под URL:

```text
https://r7zex.github.io/vk_handshakes/auth-helper/
```
