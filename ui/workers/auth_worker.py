from PySide6.QtCore import QObject, Signal, Slot

from utils.get_token import get_token_from_site


class AuthWorker(QObject):
    finished = Signal(bool, str)

    @Slot()
    def run(self) -> None:
        try:
            token = get_token_from_site()
            if not token:
                self.finished.emit(False, "Не удалось получить access_token")
                return

            self.finished.emit(True, token)

        except Exception as exc:
            self.finished.emit(False, str(exc))