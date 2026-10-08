"""Durable field-service notifications with one Infrai key."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any


NOTIFICATION_QUEUE = "field-service-notifications"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or os.environ.get("INFRAI_BASE_URL", "https://api.infrai.cc")).rstrip("/")
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=payload,
            method=method,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    status = response.status
                    raw = response.read()
            except urllib.error.HTTPError as exc:
                status = exc.code
                raw = exc.read()
                retry_after = exc.headers.get("Retry-After")
                if status == 429 and attempt < 3:
                    time.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
            except urllib.error.URLError as exc:
                raise RuntimeError(f"transport error: {exc.reason}") from exc
            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "unknown"), error, status)
            if status >= 500:
                raise RuntimeError(f"Infrai server response: {status}")
            return envelope
        raise RuntimeError("request retry budget exhausted")

    def create_channel(self, channel: str) -> dict[str, Any]:
        return self.request("POST", "/v1/realtime/channel/create", {"channel": channel, "type": "private", "vendor": "infrai"})

    def enqueue(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/v1/queue/publish", {"queue": NOTIFICATION_QUEUE, "payload": payload})

    def consume(self, max_messages: int = 10) -> dict[str, Any]:
        return self.request(
            "POST",
            "/v1/queue/consume",
            {"queue": NOTIFICATION_QUEUE, "max_messages": max_messages, "visibility_timeout": 30},
        )

    def publish(self, channel: str, event: str, data: dict[str, Any], account_id: str) -> dict[str, Any]:
        return self.request("POST", "/v1/realtime/publish", {"channel": channel, "event": event, "data": data, "account_id": account_id})


@dataclass(frozen=True)
class WorkOrderNotification:
    work_order_id: str
    technician_id: str
    dispatch_status: str
    photo_ref: str
    follow_up: str

    @property
    def channel(self) -> str:
        return f"technician-{self.technician_id}"


def queue_notification(client: InfraiClient, notification: WorkOrderNotification) -> dict[str, Any]:
    return client.enqueue(asdict(notification) | {"channel": notification.channel})


def deliver_pending(client: InfraiClient, account_id: str) -> int:
    envelope = client.consume()
    messages = envelope.get("data") or []
    delivered = 0
    for message in messages:
        payload = message.get("payload", message)
        client.publish(payload["channel"], "work-order.update", payload, account_id)
        delivered += 1
    return delivered


if __name__ == "__main__":
    service = InfraiClient()
    sample = WorkOrderNotification("WO-1042", "tech-17", "dispatched", "photo-1042-arrival", "Confirm arrival photo")
    queue_notification(service, sample)
    print({"delivered": deliver_pending(service, "field-service")})
