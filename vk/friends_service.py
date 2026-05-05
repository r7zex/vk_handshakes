class FriendsService:
    def __init__(self, client):
        self.client = client

    def get_friends(self, user_id: int, limit: int) -> list[int]:
        data = self.client.friends_get_direct(user_id=user_id, count=limit)
        return data.get("items", [])

    def probe_is_hub(self, user_id: int) -> bool:
        return False
