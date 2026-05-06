import time
from collections import deque

from search.models import SearchResult, SearchSettings
from utils.formatting import format_user_url
from vk.errors import SearchCancelledError


def bidirectional_bfs(
    client,
    friends_service,
    start_id: int,
    end_id: int,
    settings: SearchSettings,
    blacklist: set[int] | None = None,
    progress_callback=None,
    cancel_checker=None,
) -> SearchResult:
    started = time.time()
    blacklist = blacklist or set()
    progress_callback = progress_callback or (lambda *_: None)

    def emit(message: str) -> None:
        progress_callback(message)

    def check_cancel() -> None:
        if cancel_checker and cancel_checker():
            raise SearchCancelledError()

    def make_result(found: bool, path: list[int] | None, message: str) -> SearchResult:
        final_path = path or []
        return SearchResult(
            found=found,
            path=final_path,
            path_urls=[format_user_url(uid) for uid in final_path],
            depth=max(len(final_path) - 1, 0) if found else settings.max_depth,
            message=message,
            processed_users=processed_users,
            vk_requests_count=client.requests_count,
            elapsed_seconds=time.time() - started,
        )

    def emit_layer_progress(side: str, queue: deque[tuple[int, int]], depth: int) -> None:
        key = (side, depth)
        if key not in layer_totals:
            layer_totals[key] = 1 + sum(1 for _, item_depth in queue if item_depth == depth)
            layer_processed[key] = 0

        layer_processed[key] += 1
        emit(
            f"{side}, рукопожатие {depth}, "
            f"обработано профилей {layer_processed[key]}/{layer_totals[key]}"
        )

    processed_users = 0
    hub_cache: set[int] = set()
    friends_cache: dict[tuple[int, bool], list[int]] = {}
    profile_cache: dict[int, dict] = {}
    layer_totals: dict[tuple[str, int], int] = {}
    layer_processed: dict[tuple[str, int], int] = {}

    if start_id == end_id:
        return SearchResult(
            found=True,
            path=[start_id],
            path_urls=[format_user_url(start_id)],
            depth=0,
            message="Одинаковые пользователи",
            elapsed_seconds=time.time() - started,
        )

    visited_fwd: dict[int, int | None] = {start_id: None}
    visited_bwd: dict[int, int | None] = {end_id: None}

    queue_fwd: deque[tuple[int, int]] = deque([(start_id, 0)])
    queue_bwd: deque[tuple[int, int]] = deque([(end_id, 0)])

    def reconstruct_path(meeting_point: int) -> list[int]:
        path_fwd: list[int] = []
        node: int | None = meeting_point

        while node is not None:
            path_fwd.append(node)
            node = visited_fwd[node]

        path_fwd.reverse()

        path_bwd: list[int] = []
        node = visited_bwd[meeting_point]

        while node is not None:
            path_bwd.append(node)
            node = visited_bwd[node]

        return path_fwd + path_bwd

    max_side_depth = settings.max_depth // 2

    while queue_fwd and queue_bwd:
        check_cancel()

        if len(queue_fwd) <= len(queue_bwd):
            current_queue = queue_fwd
            current_visited = visited_fwd
            other_visited = visited_bwd
            side = "с начала"
        else:
            current_queue = queue_bwd
            current_visited = visited_bwd
            other_visited = visited_fwd
            side = "с конца"

        user_id, depth = current_queue.popleft()

        if depth >= max_side_depth:
            continue

        processed_users += 1
        emit_layer_progress(side, current_queue, depth)

        is_root = depth == 0
        friends = friends_service.get_friends(
            user_id=user_id,
            settings=settings,
            force=is_root,
            hub_cache=hub_cache,
            friends_cache=friends_cache,
            profile_cache=profile_cache,
            progress_callback=None,
            cancel_checker=cancel_checker,
        )

        if is_root and not friends:
            emit(f"{side}, рукопожатие {depth}, список друзей пуст или недоступен")

        for friend_id in friends:
            check_cancel()

            if friend_id in blacklist:
                continue

            if settings.exclude_hubs and friend_id in hub_cache:
                continue

            if settings.forbid_direct_connection and (
                (user_id == start_id and friend_id == end_id)
                or (user_id == end_id and friend_id == start_id)
            ):
                continue

            if friend_id in current_visited:
                continue

            current_visited[friend_id] = user_id
            current_queue.append((friend_id, depth + 1))

            if friend_id in other_visited:
                if settings.exclude_hubs and friends_service.probe_is_hub(
                    friend_id,
                    settings,
                    hub_cache,
                    progress_callback=None,
                    cancel_checker=cancel_checker,
                ):
                    continue

                path = reconstruct_path(friend_id)
                emit(f"Точка встречи фронтов: id{friend_id}")
                return make_result(
                    True,
                    path,
                    f"Найден путь длиной {len(path) - 1} рукопожатий",
                )

    return make_result(
        False,
        None,
        f"Путь не найден в пределах {settings.max_depth} рукопожатий",
    )
