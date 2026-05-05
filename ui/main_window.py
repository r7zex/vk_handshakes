from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from search.models import SearchSettings
from storage.cache_store import CacheStore
from storage.settings_store import SettingsStore
from storage.token_store import TokenStore
from ui.workers.auth_worker import AuthWorker
from ui.workers.search_worker import SearchWorker
from utils.formatting import format_path, mask_token
from utils.validation import validate_search_form
from vk.api_client import VkApiClient
from vk.friends_service import FriendsService
from vk.token_manager import TokenManager
from vk.token_provider import ManualTokenProvider, extract_token


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VK Handshakes")
        self.resize(1100, 780)

        self.settings_store = SettingsStore()
        self.settings = self.settings_store.load_settings()
        self.token_store = TokenStore()
        self.cache_store = CacheStore()
        self.manual_provider = ManualTokenProvider()
        self.token_manager = TokenManager(
            self.token_store,
            self.manual_provider,
            self._validate_token,
        )
        self.client = VkApiClient(self.token_manager)
        self.friends_service = FriendsService(self.client, self.cache_store)

        self.auth_worker = None
        self.auth_thread = None
        self.search_worker = None
        self.search_thread = None
        self.last_result = None
        self.token_ok = False

        self._build_ui()
        if self.token_manager.has_token():
            self.check_token_async()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("VK Handshakes")
        title.setObjectName("Title")
        subtitle = QLabel("Поиск кратчайшей цепочки рукопожатий ВКонтакте")
        subtitle.setObjectName("Subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        auth = QGroupBox("Авторизация")
        auth_form = QFormLayout(auth)
        self.auth_label = QLabel("Токен не найден")
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Вставьте access_token или ссылку с access_token=...")
        self.token_input.setEchoMode(QLineEdit.Password)

        self.btn_save_token = QPushButton("Вставить токен вручную")
        self.btn_check_token = QPushButton("Проверить токен")
        self.btn_reset_token = QPushButton("Сбросить токен")
        self.btn_save_token.clicked.connect(self.on_save_token)
        self.btn_check_token.clicked.connect(self.check_token_async)
        self.btn_reset_token.clicked.connect(self.on_reset_token)

        auth_buttons = QHBoxLayout()
        auth_buttons.addWidget(self.btn_save_token)
        auth_buttons.addWidget(self.btn_check_token)
        auth_buttons.addWidget(self.btn_reset_token)
        auth_form.addRow("Статус", self.auth_label)
        auth_form.addRow("Токен", self.token_input)
        auth_form.addRow(auth_buttons)
        layout.addWidget(auth)

        search = QGroupBox("Поиск")
        search_form = QFormLayout(search)
        self.user1 = QLineEdit()
        self.user1.setPlaceholderText("https://vk.com/r7zex, r7zex, id123 или 123")
        self.user2 = QLineEdit()
        self.user2.setPlaceholderText("https://vk.com/durov, durov, id1 или 1")
        self.blacklist = QTextEdit()
        self.blacklist.setPlaceholderText("Чёрный список, один пользователь на строку")
        self.blacklist.setFixedHeight(80)

        self.max_depth = QSpinBox()
        self.max_depth.setRange(1, 30)
        self.max_depth.setValue(self.settings.max_depth)
        self.max_friends = QSpinBox()
        self.max_friends.setRange(1, 100000)
        self.max_friends.setValue(self.settings.max_friends_per_user)
        self.max_root = QSpinBox()
        self.max_root.setRange(1, 100000)
        self.max_root.setValue(self.settings.max_root_friends)
        self.api_delay = QDoubleSpinBox()
        self.api_delay.setRange(0.0, 30.0)
        self.api_delay.setSingleStep(0.05)
        self.api_delay.setValue(self.settings.api_delay)
        self.profile_batch_size = QSpinBox()
        self.profile_batch_size.setRange(1, 1000)
        self.profile_batch_size.setValue(self.settings.profile_batch_size)

        self.forbid_direct = QCheckBox("Запретить прямое соединение")
        self.forbid_direct.setChecked(self.settings.forbid_direct_connection)
        self.filter_closed = QCheckBox("Фильтровать закрытые профили")
        self.filter_closed.setChecked(self.settings.filter_closed_profiles)
        self.exclude_hubs = QCheckBox("Исключать хабы")
        self.exclude_hubs.setChecked(self.settings.exclude_hubs)
        self.use_cache = QCheckBox("Использовать кэш")
        self.use_cache.setChecked(self.settings.use_cache)

        search_form.addRow("Первый пользователь", self.user1)
        search_form.addRow("Второй пользователь", self.user2)
        search_form.addRow("Blacklist", self.blacklist)
        search_form.addRow("MAX_DEPTH", self.max_depth)
        search_form.addRow("MAX_FRIENDS_PER_USER", self.max_friends)
        search_form.addRow("MAX_ROOT_FRIENDS", self.max_root)
        search_form.addRow("API_DELAY", self.api_delay)
        search_form.addRow("PROFILE_BATCH_SIZE", self.profile_batch_size)
        search_form.addRow(self.forbid_direct)
        search_form.addRow(self.filter_closed)
        search_form.addRow(self.exclude_hubs)
        search_form.addRow(self.use_cache)
        layout.addWidget(search)

        buttons = QHBoxLayout()
        self.btn_start = QPushButton("Найти цепочку")
        self.btn_stop = QPushButton("Остановить")
        self.btn_clear_cache = QPushButton("Очистить кэш")
        self.btn_stop.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.on_start)
        self.btn_stop.clicked.connect(self.on_stop)
        self.btn_clear_cache.clicked.connect(self.on_clear_cache)
        buttons.addWidget(self.btn_start)
        buttons.addWidget(self.btn_stop)
        buttons.addWidget(self.btn_clear_cache)
        layout.addLayout(buttons)

        result_box = QGroupBox("Результат")
        result_layout = QVBoxLayout(result_box)
        self.result = QTextBrowser()
        self.result.setOpenExternalLinks(True)
        self.result.setMinimumHeight(120)
        result_layout.addWidget(self.result)

        result_buttons = QHBoxLayout()
        self.btn_copy = QPushButton("Скопировать путь")
        self.btn_save_txt = QPushButton("Сохранить TXT")
        self.btn_save_json = QPushButton("Сохранить JSON")
        self.btn_copy.clicked.connect(self.on_copy_path)
        self.btn_save_txt.clicked.connect(self.on_save_txt)
        self.btn_save_json.clicked.connect(self.on_save_json)
        result_buttons.addWidget(self.btn_copy)
        result_buttons.addWidget(self.btn_save_txt)
        result_buttons.addWidget(self.btn_save_json)
        result_layout.addLayout(result_buttons)
        layout.addWidget(result_box)

        log_box = QGroupBox("Лог")
        log_layout = QVBoxLayout(log_box)
        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        log_layout.addWidget(self.logs)
        layout.addWidget(log_box)

    def log(self, level: str, message: str) -> None:
        self.logs.append(f"[{level}] {message}")

    def _validate_token(self, token: str) -> bool:
        class StaticTokenManager:
            def get_valid_token(self):
                return token

            def invalidate_token(self):
                return None

            def refresh_or_reauth(self):
                return token

        tmp = VkApiClient(StaticTokenManager())
        tmp.api_delay = 0
        try:
            tmp.users_get("1")
            return True
        except Exception:
            return False

    def _settings_from_ui(self) -> SearchSettings:
        return SearchSettings(
            max_depth=self.max_depth.value(),
            max_friends_per_user=self.max_friends.value(),
            max_root_friends=self.max_root.value(),
            api_delay=self.api_delay.value(),
            profile_batch_size=self.profile_batch_size.value(),
            forbid_direct_connection=self.forbid_direct.isChecked(),
            filter_closed_profiles=self.filter_closed.isChecked(),
            exclude_hubs=self.exclude_hubs.isChecked(),
            use_cache=self.use_cache.isChecked(),
        )

    def on_save_token(self) -> None:
        token = extract_token(self.token_input.text())
        if not token:
            self.auth_label.setText("Не удалось извлечь access_token")
            return

        self.manual_provider.set_token(token)
        self.token_manager.save_token(token)
        self.token_input.clear()
        self.auth_label.setText(f"Токен сохранён: {mask_token(token)}. Проверяем...")
        self.log("auth", f"токен сохранён: {mask_token(token)}")
        self.check_token_async()

    def check_token_async(self) -> None:
        if self.auth_thread and self.auth_thread.isRunning():
            return

        self.auth_label.setText("Проверяем токен...")
        self.btn_check_token.setEnabled(False)
        self.btn_start.setEnabled(False)

        self.auth_thread = QThread(self)
        self.auth_worker = AuthWorker(self.token_manager)
        self.auth_worker.moveToThread(self.auth_thread)
        self.auth_thread.started.connect(self.auth_worker.run)
        self.auth_worker.finished.connect(self.on_auth_finished)
        self.auth_worker.finished.connect(self.auth_thread.quit)
        self.auth_thread.finished.connect(self.auth_worker.deleteLater)
        self.auth_thread.finished.connect(self.auth_thread.deleteLater)
        self.auth_thread.finished.connect(self._clear_auth_thread)
        self.auth_thread.start()

    def on_auth_finished(self, ok: bool, message: str) -> None:
        self.token_ok = ok
        self.btn_check_token.setEnabled(True)
        self.btn_start.setEnabled(ok)
        self.auth_label.setText(message)
        self.log("auth", message)

    def on_reset_token(self) -> None:
        self.manual_provider.set_token("")
        self.token_manager.delete_token()
        self.token_ok = False
        self.btn_start.setEnabled(False)
        self.auth_label.setText("Токен сброшен")
        self.log("auth", "токен удалён")

    def on_start(self) -> None:
        settings = self._settings_from_ui()
        errors = validate_search_form(self.user1.text(), self.user2.text(), settings)
        if not self.token_ok:
            errors.append("Сначала проверьте рабочий токен")
        if errors:
            self.result.setPlainText("; ".join(errors))
            return

        self.settings_store.save_settings(settings)
        self.settings = settings
        self.client.requests_count = 0
        self.friends_service.filtered_profiles_count = 0
        self.friends_service.hubs_count = 0
        self.result.setPlainText("Поиск запущен...")

        self.search_thread = QThread(self)
        self.search_worker = SearchWorker(
            self.client,
            self.friends_service,
            self.user1.text(),
            self.user2.text(),
            settings,
            self.blacklist.toPlainText(),
            self.cache_store,
        )
        self.search_worker.moveToThread(self.search_thread)
        self.search_thread.started.connect(self.search_worker.run)
        self.search_worker.progress.connect(lambda message: self.log("info", message))
        self.search_worker.finished.connect(self.on_finished)
        self.search_worker.failed.connect(self.on_failed)
        self.search_worker.finished.connect(self.search_thread.quit)
        self.search_worker.failed.connect(self.search_thread.quit)
        self.search_thread.finished.connect(self.search_worker.deleteLater)
        self.search_thread.finished.connect(self.search_thread.deleteLater)
        self.search_thread.finished.connect(self._clear_search_thread)
        self.search_thread.start()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

    def on_stop(self) -> None:
        if self.search_worker:
            self.search_worker.cancel()
            self.log("search", "запрошена остановка")

    def on_failed(self, error: str) -> None:
        self.client.logger = lambda *_: None
        self.btn_start.setEnabled(self.token_ok)
        self.btn_stop.setEnabled(False)
        self.result.setPlainText(f"Ошибка: {error}")
        self.log("error", error)

    def on_finished(self, result) -> None:
        self.client.logger = lambda *_: None
        self.last_result = result
        self.btn_start.setEnabled(self.token_ok)
        self.btn_stop.setEnabled(False)

        if result.found:
            links = "<br>".join(
                f'<a href="{url}">{url}</a>' for url in result.path_urls
            )
            chain = " → ".join(
                f'<a href="{url}">id{uid}</a>'
                for uid, url in zip(result.path, result.path_urls, strict=True)
            )
            self.result.setHtml(
                f"<b>{result.message}</b><br><br>{links}<br><br>{chain}"
            )
            self.log("result", result.message)
        else:
            self.result.setPlainText(
                f"{result.message}\n"
                f"VK-запросов: {result.vk_requests_count}, "
                f"обработано пользователей: {result.processed_users}"
            )

    def on_copy_path(self) -> None:
        if self.last_result and self.last_result.path:
            QApplication.clipboard().setText(format_path(self.last_result.path))
            self.log("result", "путь скопирован")

    def on_save_txt(self) -> None:
        if not self.last_result:
            return
        file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить TXT", "", "Text (*.txt)")
        if not file_name:
            return
        Path(file_name).write_text(self.result.toPlainText(), encoding="utf-8")
        self.log("result", f"TXT сохранён: {file_name}")

    def on_save_json(self) -> None:
        if not self.last_result:
            return
        file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить JSON", "", "JSON (*.json)")
        if not file_name:
            return
        Path(file_name).write_text(
            self.last_result.model_dump_json(indent=2),
            encoding="utf-8",
        )
        self.log("result", f"JSON сохранён: {file_name}")

    def on_clear_cache(self) -> None:
        self.cache_store.clear_cache()
        self.log("cache", "кэш очищен")

    def _clear_auth_thread(self) -> None:
        self.auth_worker = None
        self.auth_thread = None

    def _clear_search_thread(self) -> None:
        self.search_worker = None
        self.search_thread = None
