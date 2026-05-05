from PySide6.QtCore import QObject, Signal, Slot


class AuthWorker(QObject):
    finished = Signal(bool, str)

    def __init__(self, token_manager):
        super().__init__()
        self.token_manager = token_manager

    @Slot()
    def run(self) -> None:
        try:
            self.token_manager.get_valid_token()
            self.finished.emit(True, "Авторизован")
        except Exception as exc:
            self.finished.emit(False, str(exc))
