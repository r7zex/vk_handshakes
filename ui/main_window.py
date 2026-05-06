from datetime import datetime
from html import escape
from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from search.models import SearchSettings
from storage.cache_store import CacheStore
from storage.settings_store import SettingsStore
from storage.token_store import TokenStore
from ui.workers.search_worker import SearchWorker
from utils.formatting import format_path, mask_token
from utils.validation import validate_search_form
from utils.get_token import get_token_from_site
from vk.api_client import VkApiClient
from vk.friends_service import FriendsService
from vk.token_manager import TokenManager
from vk.token_provider import (
    ManualTokenProvider,
    extract_token,
)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VK Handshakes")
        self.resize(1180, 820)

        self.settings_store = SettingsStore()
        self.settings = self.settings_store.load_settings()
        self.token_store = TokenStore()
        self.cache_store = CacheStore()
        self.manual_provider = ManualTokenProvider()
        self.token_manager = TokenManager(self.token_store, self.manual_provider)
        self.client = VkApiClient(self.token_manager)
        self.friends_service = FriendsService(self.client, self.cache_store)

        self.auth_worker = None
        self.auth_thread = None
        self.search_worker = None
        self.search_thread = None
        self.last_result = None

        self._build_ui()
        self._render_empty_result()
        self.log("info", "Готово к работе. Вставьте токен и нажмите «Сохранить токен».")

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(10)

        title = QLabel("VK Handshakes")
        title.setObjectName("Title")
        subtitle = QLabel("Поиск кратчайшей цепочки рукопожатий ВКонтакте")
        subtitle.setObjectName("Subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        workspace = QGridLayout()
        workspace.setColumnStretch(0, 3)
        workspace.setColumnStretch(1, 2)
        workspace.setHorizontalSpacing(12)
        workspace.setVerticalSpacing(10)

        left_column = QVBoxLayout()
        left_column.setSpacing(10)
        left_column.addWidget(self._build_auth_box())
        left_column.addWidget(self._build_search_box())
        left_column.addLayout(self._build_action_buttons())
        left_column.addStretch(1)

        workspace.addLayout(left_column, 0, 0)
        workspace.addWidget(self._build_log_box(), 0, 1)
        layout.addLayout(workspace, stretch=4)

        layout.addWidget(self._build_result_box(), stretch=2)

    def _build_auth_box(self) -> QGroupBox:
        auth = QGroupBox("Авторизация")
        auth_form = QFormLayout(auth)
        auth_form.setLabelAlignment(auth_form.labelAlignment())

        self.auth_label = QLabel("Токен не найден")
        self.auth_label.setObjectName("AuthStatus")
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Вставьте VK-токен или ссылку с ним")

        self.btn_save_token = QPushButton("Сохранить токен")
        self.btn_reset_token = QPushButton("Сбросить токен")
        self.btn_auto_token = QPushButton("Вставить автоматически (требуется авторизация через ВК)")

        self.btn_save_token.clicked.connect(self.on_save_token)
        self.btn_reset_token.clicked.connect(self.on_reset_token)
        self.btn_auto_token.clicked.connect(self.on_auto_token)

        auth_buttons = QGridLayout()
        auth_buttons.addWidget(self.btn_save_token, 0, 0)
        auth_buttons.addWidget(self.btn_reset_token, 0, 1)
        auth_buttons.addWidget(self.btn_auto_token, 1, 0, 1, 2)

        auth_form.addRow("Статус", self.auth_label)
        auth_form.addRow("Токен", self.token_input)
        auth_form.addRow(auth_buttons)
        return auth

    def _build_search_box(self) -> QGroupBox:
        search = QGroupBox("Поиск")
        form = QFormLayout(search)

        self.user1 = QLineEdit()
        self.user1.setPlaceholderText("r7zex, id123, 123 или https://vk.com/r7zex")
        self.user2 = QLineEdit()
        self.user2.setPlaceholderText("durov, id1, 1 или https://vk.com/durov")
        self.ignored_profiles = QLineEdit()
        self.ignored_profiles.setPlaceholderText("id123, r7zex, https://vk.com/name")

        self.max_depth = QSpinBox()
        self.max_depth.setRange(1, 30)
        self.max_depth.setValue(self.settings.max_depth)
        self.max_friends = QSpinBox()
        self.max_friends.setRange(1, 100000)
        self.max_friends.setValue(self.settings.max_friends_per_user)

        self.forbid_direct = QCheckBox("Не учитывать прямую дружбу")
        self.forbid_direct.setChecked(self.settings.forbid_direct_connection)
        self.use_cache = QCheckBox("Использовать кэш")
        self.use_cache.setChecked(self.settings.use_cache)

        form.addRow("Начальный пользователь", self.user1)
        form.addRow("Конечный пользователь", self.user2)
        form.addRow("Не учитывать в рукопожатиях", self.ignored_profiles)
        form.addRow("Макс кол-во рукопожатий", self.max_depth)
        form.addRow("Макс кол-во друзей у пользователя", self.max_friends)
        form.addRow(self.forbid_direct)
        form.addRow(self.use_cache)
        return search

    def _build_action_buttons(self) -> QHBoxLayout:
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
        return buttons

    def _build_log_box(self) -> QGroupBox:
        log_box = QGroupBox("Журнал действий")
        log_layout = QVBoxLayout(log_box)
        self.logs = QTextBrowser()
        self.logs.setObjectName("LogPanel")
        self.logs.setOpenExternalLinks(False)
        log_layout.addWidget(self.logs)
        return log_box

    def _build_result_box(self) -> QGroupBox:
        result_box = QGroupBox("Результат")
        result_layout = QVBoxLayout(result_box)
        self.result = QTextBrowser()
        self.result.setObjectName("ResultPanel")
        self.result.setOpenExternalLinks(True)
        self.result.setMinimumHeight(170)
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
        return result_box

    def log(self, level: str, message: str) -> None:
        colors = {
            "auth": "#60a5fa",
            "cache": "#a78bfa",
            "error": "#f87171",
            "info": "#d1d5db",
            "result": "#34d399",
            "search": "#93c5fd",
            "success": "#34d399",
            "warning": "#fbbf24",
        }
        color = colors.get(level, "#d1d5db")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(
            "<div class='log-line'>"
            f"<span style='color:#64748b'>{timestamp}</span> "
            f"<span style='color:{color}; font-weight:700'>[{escape(level)}]</span> "
            f"<span style='color:#e5e7eb'>{escape(message)}</span>"
            "</div>"
        )
        self.logs.verticalScrollBar().setValue(self.logs.verticalScrollBar().maximum())

    def _settings_from_ui(self) -> SearchSettings:
        defaults = SearchSettings()
        return SearchSettings(
            max_depth=self.max_depth.value(),
            max_friends_per_user=self.max_friends.value(),
            max_root_friends=defaults.max_root_friends,
            api_delay=defaults.api_delay,
            profile_batch_size=defaults.profile_batch_size,
            forbid_direct_connection=self.forbid_direct.isChecked(),
            filter_closed_profiles=True,
            exclude_hubs=True,
            use_cache=self.use_cache.isChecked(),
        )

    def _render_empty_result(self) -> None:
        self.result.setHtml(
            """
            <div style="color:#e5e7eb">
              <h2 style="margin:0 0 8px 0">Результат появится здесь</h2>
              <p style="margin:0; color:#94a3b8">
                После запуска поиска здесь будет длина цепочки, кликабельные ссылки
                и строка пути для копирования.
              </p>
            </div>
            """
        )

    def on_save_token(self) -> None:
        token = extract_token(self.token_input.text())
        if not token:
            self.auth_label.setText("Не удалось извлечь токен")
            self.log("warning", "Вставьте чистый токен или ссылку, где он есть")
            return

        self.manual_provider.set_token(token)
        self.token_manager.save_token(token)
        self.token_input.clear()
        self.btn_start.setEnabled(True)
        self.auth_label.setText(f"Токен сохранён: {mask_token(token)}.")
        self.log("auth", f"токен сохранён: {mask_token(token)}")

    def on_reset_token(self) -> None:
        self.manual_provider.set_token("")
        self.token_manager.delete_token()
        self.btn_start.setEnabled(False)
        self.auth_label.setText("Токен сброшен")
        self.log("auth", "токен удалён")

    def on_auto_token(self) -> None:
        token = get_token_from_site()
        self.manual_provider.set_token(token)
        self.token_manager.save_token(token)
        self.token_input.clear()
        self.btn_start.setEnabled(True)
        self.auth_label.setText(f"Токен сохранён: {mask_token(token)}.")
        self.log("auth", f"токен сохранён: {mask_token(token)}")
        self.log(
            "auth",
            "кнопка автоматической вставки токена добавлена; обработчик авторизации ещё не подключён",
        )

    def on_start(self) -> None:
        if self.search_thread and self.search_thread.isRunning():
            return

        settings = self._settings_from_ui()
        self.btn_start.setEnabled(False)
        errors = validate_search_form(self.user1.text(), self.user2.text(), settings)
        if errors:
            self.result.setPlainText("; ".join(errors))
            self.log("warning", "; ".join(errors))
            self.btn_start.setEnabled(True)
            return

        self.settings_store.save_settings(settings)
        self.settings = settings
        self.client.requests_count = 0
        self.friends_service.filtered_profiles_count = 0
        self.friends_service.hubs_count = 0
        self.result.setHtml("<b>Поиск запущен...</b>")

        self.search_thread = QThread(self)
        self.search_worker = SearchWorker(
            self.client,
            self.friends_service,
            self.user1.text(),
            self.user2.text(),
            settings,
            self.ignored_profiles.text(),
            self.cache_store,
        )
        self.search_worker.moveToThread(self.search_thread)
        self.search_thread.started.connect(self.search_worker.run)
        self.search_worker.progress.connect(lambda message: self.log("search", message))
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
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.result.setPlainText(f"Ошибка: {error}")
        self.log("error", error)

    def on_finished(self, result) -> None:
        self.client.logger = lambda *_: None
        self.last_result = result
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

        if result.found:
            self._render_found_result(result)
            self.log("result", result.message)
        else:
            self._render_not_found_result(result)
            self.log("warning", result.message)

    def _render_found_result(self, result) -> None:
        links = "".join(
            (
                "<li style='margin:4px 0'>"
                f"<a href='{escape(url)}' style='color:#60a5fa'>{escape(url)}</a>"
                "</li>"
            )
            for url in result.path_urls
        )
        chain = " → ".join(
            f"<a href='{escape(url)}' style='color:#93c5fd'>id{uid}</a>"
            for uid, url in zip(result.path, result.path_urls, strict=True)
        )
        self.result.setHtml(
            f"""
            <div style="color:#e5e7eb">
              <div style="font-size:18px; font-weight:800; color:#34d399">
                {escape(result.message)}
              </div>
              <div style="margin-top:8px; color:#94a3b8">
                Обработано: {result.processed_users} профилей ·
                VK-запросов: {result.vk_requests_count} ·
                Время: {result.elapsed_seconds:.1f} сек.
              </div>
              <ol style="margin-top:12px; padding-left:22px">{links}</ol>
              <div style="margin-top:12px; padding:10px; border:1px solid #334155;
                          border-radius:8px; background:#0f172a">
                {chain}
              </div>
            </div>
            """
        )

    def _render_not_found_result(self, result) -> None:
        self.result.setHtml(
            f"""
            <div style="color:#e5e7eb">
              <div style="font-size:18px; font-weight:800; color:#fbbf24">
                {escape(result.message)}
              </div>
              <p style="color:#94a3b8">
                Попробуйте увеличить максимальную длину пути или лимит друзей на шаг.
              </p>
              <p style="color:#94a3b8">
                VK-запросов: {result.vk_requests_count},
                обработано профилей: {result.processed_users}
              </p>
            </div>
            """
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

    def closeEvent(self, event) -> None:
        if self.search_worker:
            self.search_worker.cancel()
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.quit()
            self.search_thread.wait(3000)
        event.accept()
