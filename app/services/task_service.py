import json
from typing import Protocol
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging_config import logger
from app.db.models import TaskModel
from app.schemas.task import AnalyticsOut
from app.services.cache import CacheProvider, cache_provider


class NotificationDispatcher(Protocol):
    def send_urgent_alert(self, recipient_email: str, task_title: str) -> None: ...


class LogNotificationDispatcher:
    """Production background worker adapter that dispatches urgent alerts asynchronously."""

    def send_urgent_alert(self, recipient_email: str, task_title: str) -> None:
        logger.info(
            f"[BACKGROUND_JOB] Urgent task alert dispatched | recipient={recipient_email} | task='{task_title}'"
        )


class FakeNotificationDispatcher:
    """In-memory spy dispatcher for automated unit/API tests."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_urgent_alert(self, recipient_email: str, task_title: str) -> None:
        self.sent.append((recipient_email, task_title))


notification_dispatcher: NotificationDispatcher = LogNotificationDispatcher()


class TaskService:
    def __init__(
        self,
        cache: CacheProvider = cache_provider,
        dispatcher: NotificationDispatcher = notification_dispatcher,
    ) -> None:
        self.cache = cache
        self.dispatcher = dispatcher

    @staticmethod
    def _analytics_cache_key(user_id: int) -> str:
        return f"analytics:user:{user_id}"

    def invalidate_user_analytics(self, user_id: int) -> None:
        key = self._analytics_cache_key(user_id)
        self.cache.delete(key)
        logger.debug(f"analytics_cache_invalidated | user_id={user_id}")

    def get_user_analytics(self, db: Session, user_id: int) -> AnalyticsOut:
        key = self._analytics_cache_key(user_id)
        cached_raw = self.cache.get(key)

        if cached_raw is not None:
            logger.info(f"analytics_cache_hit | user_id={user_id}")
            data = json.loads(cached_raw)
            data["cached"] = True
            return AnalyticsOut(**data)

        logger.info(f"analytics_cache_miss | user_id={user_id}")
        tasks = db.query(TaskModel).filter(TaskModel.owner_id == user_id).all()

        total = len(tasks)
        todo = sum(1 for t in tasks if t.status == "TODO")
        in_progress = sum(1 for t in tasks if t.status == "IN_PROGRESS")
        done = sum(1 for t in tasks if t.status == "DONE")
        archived = sum(1 for t in tasks if t.status == "ARCHIVED")
        urgent_count = sum(1 for t in tasks if t.priority == "URGENT")
        completion_rate = round((done / total) * 100, 2) if total > 0 else 0.0

        result = AnalyticsOut(
            total=total,
            todo=todo,
            in_progress=in_progress,
            done=done,
            archived=archived,
            urgent_count=urgent_count,
            completion_rate=completion_rate,
            cached=False,
        )

        self.cache.set(
            key,
            result.model_dump_json(),
            ttl_seconds=settings.ANALYTICS_CACHE_TTL_SECONDS,
        )
        return result


task_service = TaskService()