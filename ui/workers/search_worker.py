from PySide6.QtCore import QObject, Signal, Slot

from search.bfs import bidirectional_bfs


class SearchWorker(QObject):
    progress = Signal(str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, client, friends_service, start_id, end_id, settings, blacklist):
        super().__init__()
        self.client = client
        self.friends_service = friends_service
        self.start_id = start_id
        self.end_id = end_id
        self.settings = settings
        self.blacklist = blacklist
        self._cancel = False

    def cancel(self):
        self._cancel = True

    @Slot()
    def run(self):
        try:
            result = bidirectional_bfs(self.client, self.friends_service, self.start_id, self.end_id, self.settings, self.blacklist, progress_callback=self.progress.emit, cancel_checker=lambda: self._cancel)
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
