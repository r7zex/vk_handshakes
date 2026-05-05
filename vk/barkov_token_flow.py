from __future__ import annotations

from dataclasses import dataclass

from app.config import CONFIG


@dataclass(slots=True)
class BarkovTokenRequest:
    """Input for the future vk.barkov.net token bootstrap flow.

    vk_profile_input is optional because VK OAuth Implicit Flow can return
    user_id in the redirect fragment together with access_token. Keep this
    field as a fallback for the barkov form if the authenticated user id is
    unavailable or differs from the page that should be collected.
    """

    vk_profile_input: str | None = None
    helper_url: str = CONFIG.github_pages_auth_helper_url
    barkov_url: str = CONFIG.barkov_base_url


@dataclass(slots=True)
class CapturedVkRequest:
    """Network request candidate captured from the embedded browser/devtools layer."""

    url: str
    method: str = "GET"
    source: str = "network"


@dataclass(slots=True)
class BarkovTokenResult:
    access_token: str | None
    auth_user_id: int | None = None
    captured_url: str | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return bool(self.access_token)


class BarkovTokenAcquirer:
    """TODO scaffold for automatic token acquisition through vk.barkov.net.

    Intended final flow:
    1. Open https://vk.barkov.net/.
    2. Select "Друзья и подписчики".
    3. Open "Сбор друзей и подписчиков".
    4. Trigger "Войти через VK" and let the user authorize the website.
    5. Resolve the VK user id:
       - first try auth_user_id returned by OAuth redirect;
       - fallback to BarkovTokenRequest.vk_profile_input.
    6. Fill the page id/profile field.
    7. Click "Собрать друзей и подписчиков страницы".
    8. Intercept network requests to vkresult.ru/method/users.get or other
       vkresult.ru/method/* endpoints and extract access_token from the URL.

    Keep this class token-safe:
    - never log the full captured URL;
    - never log the full access_token;
    - return the token only to TokenManager.
    """

    def __init__(self, logger_callback=None):
        self.logger = logger_callback or (lambda *_: None)

    def acquire_token(self, request: BarkovTokenRequest | None = None) -> BarkovTokenResult:
        request = request or BarkovTokenRequest()
        self.logger(
            "warning",
            "[auth] Автоматическое получение токена подготовлено, но browser-flow TODO ещё не заполнен.",
        )

        # TODO(token-flow): implement browser automation here.
        # Recommended options:
        # - Playwright persistent Chromium profile for reliable network events;
        # - Qt WebEngine + remote debugging if you want to keep it inside PySide.
        #
        # Pseudocode:
        # browser = launch_browser_with_network_capture()
        # page = browser.open(request.barkov_url)
        # self.open_friends_followers_section(page)
        # self.open_collect_friends_followers_tool(page)
        # auth_user_id = self.login_with_vk(page)
        # profile = request.vk_profile_input or auth_user_id
        # self.fill_vk_profile(page, profile)
        # self.click_collect_button(page)
        # captured = self.wait_for_vkresult_request(page)
        # token = self.extract_access_token_from_request(captured)
        # return BarkovTokenResult(token, auth_user_id, captured.url)

        return BarkovTokenResult(
            access_token=None,
            error="TODO: реализовать browser automation и парсинг network-запроса",
        )

    def open_friends_followers_section(self, page) -> None:
        # TODO(token-flow): click/select "Друзья и подписчики" on vk.barkov.net.
        raise NotImplementedError

    def open_collect_friends_followers_tool(self, page) -> None:
        # TODO(token-flow): open "Сбор друзей и подписчиков".
        raise NotImplementedError

    def login_with_vk(self, page) -> int | None:
        # TODO(token-flow): click "Войти через VK", wait for OAuth completion.
        # If the redirect/hash contains user_id, return it here.
        raise NotImplementedError

    def fill_vk_profile(self, page, vk_profile_input: str | int) -> None:
        # TODO(token-flow): fill the page/profile input on the Barkov tool page.
        raise NotImplementedError

    def click_collect_button(self, page) -> None:
        # TODO(token-flow): click "Собрать друзей и подписчиков страницы".
        raise NotImplementedError

    def wait_for_vkresult_request(self, page) -> CapturedVkRequest:
        # TODO(token-flow): wait until a request to vkresult.ru/method/* appears.
        raise NotImplementedError

    def extract_access_token_from_request(
        self,
        captured_request: CapturedVkRequest,
    ) -> BarkovTokenResult:
        # TODO(token-parser): implement this yourself.
        # Input example:
        # https://vkresult.ru/method/users.get?...&access_token=<token>&callback=...
        #
        # Return:
        # BarkovTokenResult(access_token=token, captured_url=sanitized_or_none)
        #
        # Do not store or log the raw URL because it contains access_token.
        return BarkovTokenResult(
            access_token=None,
            captured_url=None,
            error="TODO: распарсить access_token из CapturedVkRequest.url",
        )
