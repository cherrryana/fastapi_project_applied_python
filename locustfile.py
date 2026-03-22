from locust import HttpUser, task, between


class LinkUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """
        Создаем одну ссылку при старте юзера
        """
        resp = self.client.post(
            "/links/shorten",
            json={"url": "https://example.com/loadtest"},
        )
        self.short_code = resp.json().get("short_code", "test")

    @task(3)
    def redirect(self):
        self.client.get(
            f"/links/{self.short_code}",
            allow_redirects=False,
            name="/links/[short_code]",
        )

    @task(1)
    def get_stats(self):
        self.client.get(
            f"/links/{self.short_code}/stats",
            name="/links/[short_code]/stats",
        )

    @task(1)
    def create_link(self):
        self.client.post(
            "/links/shorten",
            json={"url": "https://example.com/new"},
        )
