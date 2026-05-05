from PySide6.QtCore import QThread
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLineEdit, QTextEdit, QPushButton, QLabel, QSpinBox, QHBoxLayout

from search.models import SearchSettings
from storage.settings_store import SettingsStore
from storage.token_store import TokenStore
from ui.workers.search_worker import SearchWorker
from utils.formatting import format_path, mask_token
from utils.validation import validate_search_form
from vk.api_client import VkApiClient
from vk.friends_service import FriendsService
from vk.token_manager import TokenManager
from vk.token_provider import ManualTokenProvider
from vk.user_resolver import resolve_blacklist, resolve_user_id


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VK Handshakes")
        self.resize(1100, 780)
        self.settings_store = SettingsStore()
        self.settings = self.settings_store.load_settings()
        self.token_store = TokenStore()
        self.manual_provider = ManualTokenProvider()
        self.token_manager = TokenManager(self.token_store, self.manual_provider, self._validate_token)
        self.client = VkApiClient(self.token_manager, self.log)
        self.friends_service = FriendsService(self.client)
        self.search_worker = None
        self.search_thread = None
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        self.auth_label = QLabel("Токен: не проверен")
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Вставьте VK access_token")
        btn_token = QPushButton("Сохранить токен")
        btn_token.clicked.connect(self.on_save_token)

        auth = QGroupBox("Авторизация")
        aform = QFormLayout(auth)
        aform.addRow(self.auth_label)
        aform.addRow(self.token_input, btn_token)

        self.user1 = QLineEdit(); self.user2 = QLineEdit(); self.blacklist = QTextEdit()
        self.max_depth = QSpinBox(); self.max_depth.setValue(self.settings.max_depth)
        self.max_friends = QSpinBox(); self.max_friends.setMaximum(100000); self.max_friends.setValue(self.settings.max_friends_per_user)
        self.max_root = QSpinBox(); self.max_root.setMaximum(100000); self.max_root.setValue(self.settings.max_root_friends)

        form = QGroupBox("Поиск")
        f = QFormLayout(form)
        f.addRow("Пользователь 1", self.user1); f.addRow("Пользователь 2", self.user2)
        f.addRow("Blacklist", self.blacklist); f.addRow("MAX_DEPTH", self.max_depth)
        f.addRow("MAX_FRIENDS", self.max_friends); f.addRow("MAX_ROOT", self.max_root)

        btns = QHBoxLayout()
        self.btn_start = QPushButton("Найти цепочку")
        self.btn_stop = QPushButton("Остановить")
        self.btn_stop.setEnabled(False)
        self.btn_start.clicked.connect(self.on_start)
        self.btn_stop.clicked.connect(self.on_stop)
        btns.addWidget(self.btn_start); btns.addWidget(self.btn_stop)

        self.result = QLabel("Результат: —")
        self.logs = QTextEdit(); self.logs.setReadOnly(True)
        lay.addWidget(auth); lay.addWidget(form); lay.addLayout(btns); lay.addWidget(self.result); lay.addWidget(self.logs)

    def log(self, level: str, msg: str):
        self.logs.append(f"[{level}] {msg}")

    def _validate_token(self, token: str) -> bool:
        tmp = VkApiClient(type("T", (), {"get_valid_token": lambda _s: token, "invalidate_token": lambda _s: None})())
        try:
            tmp.users_get("1")
            return True
        except Exception:
            return False

    def on_save_token(self):
        token = self.token_input.text().strip()
        if not token:
            return
        self.manual_provider.set_token(token)
        self.token_store.save_token(token)
        self.auth_label.setText(f"Токен сохранён: {mask_token(token)}")

    def on_start(self):
        errors = validate_search_form(self.user1.text(), self.user2.text())
        if errors:
            self.result.setText("; ".join(errors)); return
        settings = SearchSettings(max_depth=self.max_depth.value(), max_friends_per_user=self.max_friends.value(), max_root_friends=self.max_root.value())
        start_id = resolve_user_id(self.client, self.user1.text())
        end_id = resolve_user_id(self.client, self.user2.text())
        blacklist = resolve_blacklist(self.client, self.blacklist.toPlainText())

        self.search_thread = QThread(self)
        self.search_worker = SearchWorker(self.client, self.friends_service, start_id, end_id, settings, blacklist)
        self.search_worker.moveToThread(self.search_thread)
        self.search_thread.started.connect(self.search_worker.run)
        self.search_worker.progress.connect(lambda m: self.log("info", m))
        self.search_worker.finished.connect(self.on_finished)
        self.search_worker.failed.connect(lambda e: self.result.setText(f"Ошибка: {e}"))
        self.search_worker.finished.connect(self.search_thread.quit)
        self.search_worker.failed.connect(self.search_thread.quit)
        self.search_thread.start()
        self.btn_start.setEnabled(False); self.btn_stop.setEnabled(True)

    def on_stop(self):
        if self.search_worker:
            self.search_worker.cancel()

    def on_finished(self, result):
        self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False)
        if result.found:
            self.result.setText(f"Найден путь: {format_path(result.path)}")
        else:
            self.result.setText(result.message)
