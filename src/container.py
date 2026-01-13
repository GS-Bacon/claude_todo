"""Dependency injection container."""

from dataclasses import dataclass, field
from typing import TypeVar, Generic, Callable, Optional, Any

from src.domain.protocols import TaskRepository, CacheRepository, NotificationSender


T = TypeVar("T")


class Provider(Generic[T]):
    """Lazy provider that creates instance on first access."""

    def __init__(self, factory: Callable[[], T]) -> None:
        self._factory = factory
        self._instance: Optional[T] = None

    def get(self) -> T:
        """Get the instance, creating it if necessary."""
        if self._instance is None:
            self._instance = self._factory()
        return self._instance

    def reset(self) -> None:
        """Reset the instance (for testing)."""
        self._instance = None

    def override(self, instance: T) -> None:
        """Override with a specific instance (for testing)."""
        self._instance = instance


@dataclass
class Container:
    """Dependency injection container."""

    # Repositories
    _task_repository: Optional[Provider[TaskRepository]] = None
    _personal_task_repository: Optional[Provider[TaskRepository]] = None
    _cache_repository: Optional[Provider[CacheRepository]] = None

    # Notification senders
    _notification_senders: list[Provider[NotificationSender]] = field(
        default_factory=list
    )

    # Settings cache
    _settings: Optional[Any] = None

    @property
    def task_repository(self) -> TaskRepository:
        """Get the team task repository."""
        if self._task_repository is None:
            raise RuntimeError("Task repository not configured")
        return self._task_repository.get()

    @property
    def personal_task_repository(self) -> TaskRepository:
        """Get the personal task repository."""
        if self._personal_task_repository is None:
            raise RuntimeError("Personal task repository not configured")
        return self._personal_task_repository.get()

    @property
    def cache_repository(self) -> CacheRepository:
        """Get the cache repository."""
        if self._cache_repository is None:
            raise RuntimeError("Cache repository not configured")
        return self._cache_repository.get()

    @property
    def notification_senders(self) -> list[NotificationSender]:
        """Get all notification senders."""
        return [p.get() for p in self._notification_senders]

    @property
    def task_service(self) -> Any:
        """Get TaskService instance."""
        from src.services.task_service import TaskService

        return TaskService(
            team_repository=self.task_repository,
            personal_repository=self.personal_task_repository,
            cache=self.cache_repository,
        )

    @property
    def mention_service(self) -> Any:
        """Get MentionService instance."""
        from src.services.mention_service import MentionService
        from src.parsers.slack_parser import SlackWebhookParser
        from src.parsers.discord_parser import DiscordWebhookParser

        return MentionService(
            personal_repository=self.personal_task_repository,
            parsers=[SlackWebhookParser(), DiscordWebhookParser()],
        )

    @property
    def notification_service(self) -> Any:
        """Get NotificationService instance."""
        from src.services.notification_service import NotificationService

        return NotificationService(
            cache_repository=self.cache_repository,
            senders=self.notification_senders,
        )

    @property
    def settings(self) -> Any:
        """Get application settings."""
        if self._settings is None:
            from src.config.settings import get_settings

            self._settings = get_settings()
        return self._settings

    def configure_task_repository(
        self, factory: Callable[[], TaskRepository]
    ) -> "Container":
        """Configure the team task repository."""
        self._task_repository = Provider(factory)
        return self

    def configure_personal_task_repository(
        self, factory: Callable[[], TaskRepository]
    ) -> "Container":
        """Configure the personal task repository."""
        self._personal_task_repository = Provider(factory)
        return self

    def configure_cache_repository(
        self, factory: Callable[[], CacheRepository]
    ) -> "Container":
        """Configure the cache repository."""
        self._cache_repository = Provider(factory)
        return self

    def add_notification_sender(
        self, factory: Callable[[], NotificationSender]
    ) -> "Container":
        """Add a notification sender."""
        self._notification_senders.append(Provider(factory))
        return self

    def reset(self) -> None:
        """Reset all providers (for testing)."""
        if self._task_repository:
            self._task_repository.reset()
        if self._personal_task_repository:
            self._personal_task_repository.reset()
        if self._cache_repository:
            self._cache_repository.reset()
        for sender in self._notification_senders:
            sender.reset()
        self._notification_senders.clear()
        self._settings = None


# Global container instance
container = Container()


def get_container() -> Container:
    """Get the global container instance."""
    return container


def reset_container() -> None:
    """Reset the global container (for testing)."""
    global container
    container.reset()
    container = Container()
