from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
    ViewportSize,
    sync_playwright,
)


SITE_URL = "https://vk.barkov.net/followers.aspx?tag=followers"


def extract_token_from_url(url: str) -> str | None:
    if "access_token=" not in url:
        return None

    token_part = url.split("access_token=", 1)[1]
    access_token = token_part.split("&", 1)[0]
    return access_token or None


def get_token_from_site() -> str | None:
    viewport_size: ViewportSize = {"width": 900, "height": 700}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--window-size=900,700",
                "--window-position=200,100",
            ],
        )

        context = browser.new_context(viewport=viewport_size)

        page = context.new_page()
        page.goto(SITE_URL, wait_until="domcontentloaded")

        access_token = None

        try:
            with page.expect_popup(timeout=30000) as popup_info:
                page.locator('a.user-profile.liWelcome[href="/auth.aspx?ReturnUrl=/followers.aspx"]').click()

            vk_popup = popup_info.value
            vk_popup.set_viewport_size(viewport_size)

            # Человек авторизуется через ВК, после успешной авторизации окно само закрывается
            vk_popup.wait_for_url("**/wizard.aspx?**", timeout=120000)
            vk_popup.close()


            # Возвращаемся к основной странице сайта и обновляем её уже после авторизации
            page.reload(wait_until="networkidle")

            # Вводим нужное значение в поле
            # ЗАМЕНИ selector и value на свои
            page.locator('textarea[id="followUsersLinks"]').fill("1")

            def is_target_request(request) -> bool:
                url = request.url

                return (
                        "access_token=" in url
                        and "users.get" in url
                        and "vkresult.ru" in url
                    # сюда добавь ключевое слово нужного запроса:
                    # and "friends.get" in url
                    # and "followers" in url
                )

            # Нажимаем кнопку и одновременно ловим нужный Network-запрос
            with page.expect_request(is_target_request, timeout=60000) as request_info:
                page.locator('input[id="submitFollow"]').click()

            target_request = request_info.value
            access_token = extract_token_from_url(target_request.url)

        except PlaywrightTimeoutError:
            print("Не дождались авторизации или access_token")

        finally:
            context.close()
            browser.close()

        return access_token