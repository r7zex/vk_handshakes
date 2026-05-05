import time
from collections import deque

from search.models import SearchResult
from utils.formatting import format_user_url
from vk.errors import SearchCancelledError


def bidirectional_bfs(client, friends_service, start_id, end_id, settings, blacklist=None, progress_callback=None, cancel_checker=None):
    started = time.time()
    blacklist = blacklist or set()
    progress_callback = progress_callback or (lambda *_: None)

    if start_id == end_id:
        return SearchResult(found=True, path=[start_id], path_urls=[format_user_url(start_id)], depth=0, message="Одинаковые пользователи")

    q1, q2 = deque([start_id]), deque([end_id])
    p1, p2 = {start_id: None}, {end_id: None}
    d1, d2 = {start_id}, {end_id}
    depth = 0
    processed = 0

    def rebuild(meet):
        left, cur = [], meet
        while cur is not None:
            left.append(cur)
            cur = p1[cur]
        right, cur = [], p2[meet]
        while cur is not None:
            right.append(cur)
            cur = p2[cur]
        path = list(reversed(left)) + right
        return path

    while q1 and q2 and depth <= settings.max_depth:
        if cancel_checker and cancel_checker():
            raise SearchCancelledError()
        depth += 1
        for _ in range(len(q1)):
            node = q1.popleft()
            processed += 1
            for f in friends_service.get_friends(node, settings.max_friends_per_user):
                if f in blacklist or f in d1:
                    continue
                p1[f] = node
                d1.add(f)
                if f in d2:
                    path = rebuild(f)
                    return SearchResult(found=True, path=path, path_urls=[format_user_url(i) for i in path], depth=len(path)-1, message="Путь найден", processed_users=processed, vk_requests_count=client.requests_count, elapsed_seconds=time.time()-started)
                q1.append(f)
        q1, q2 = q2, q1
        p1, p2 = p2, p1
        d1, d2 = d2, d1
        progress_callback(f"[search] depth={depth} frontier={len(q1)}")

    return SearchResult(found=False, message="Путь не найден", depth=settings.max_depth, processed_users=processed, vk_requests_count=client.requests_count, elapsed_seconds=time.time()-started)
