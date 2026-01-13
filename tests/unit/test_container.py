"""Tests for dependency injection container."""

import pytest

from src.container import Container, Provider, get_container, reset_container
from src.repositories.memory import InMemoryTaskRepository, InMemoryCacheRepository


class TestProvider:
    """Tests for Provider class."""

    def test_lazy_initialization(self):
        """Should not call factory until get() is called."""
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return InMemoryTaskRepository()

        provider = Provider(factory)
        assert call_count == 0

        provider.get()
        assert call_count == 1

        # Should use cached instance
        provider.get()
        assert call_count == 1

    def test_returns_same_instance(self):
        """Should return the same instance on subsequent calls."""
        provider = Provider(InMemoryTaskRepository)

        instance1 = provider.get()
        instance2 = provider.get()

        assert instance1 is instance2

    def test_reset_clears_instance(self):
        """Should clear instance when reset() is called."""
        provider = Provider(InMemoryTaskRepository)

        instance1 = provider.get()
        provider.reset()
        instance2 = provider.get()

        assert instance1 is not instance2

    def test_override(self):
        """Should use overridden instance."""
        provider = Provider(InMemoryTaskRepository)
        override_instance = InMemoryTaskRepository()

        provider.override(override_instance)

        assert provider.get() is override_instance


class TestContainer:
    """Tests for Container class."""

    @pytest.fixture
    def container(self) -> Container:
        """Create a fresh container for each test."""
        return Container()

    def test_configure_task_repository(self, container):
        """Should configure and access task repository."""
        container.configure_task_repository(InMemoryTaskRepository)

        repo = container.task_repository
        assert isinstance(repo, InMemoryTaskRepository)

    def test_configure_personal_task_repository(self, container):
        """Should configure and access personal task repository."""
        container.configure_personal_task_repository(InMemoryTaskRepository)

        repo = container.personal_task_repository
        assert isinstance(repo, InMemoryTaskRepository)

    def test_configure_cache_repository(self, container):
        """Should configure and access cache repository."""
        container.configure_cache_repository(InMemoryCacheRepository)

        cache = container.cache_repository
        assert isinstance(cache, InMemoryCacheRepository)

    def test_unconfigured_task_repository_raises_error(self, container):
        """Should raise error when accessing unconfigured task repository."""
        with pytest.raises(RuntimeError, match="not configured"):
            _ = container.task_repository

    def test_unconfigured_personal_repository_raises_error(self, container):
        """Should raise error when accessing unconfigured personal repository."""
        with pytest.raises(RuntimeError, match="not configured"):
            _ = container.personal_task_repository

    def test_unconfigured_cache_repository_raises_error(self, container):
        """Should raise error when accessing unconfigured cache repository."""
        with pytest.raises(RuntimeError, match="not configured"):
            _ = container.cache_repository

    def test_notification_senders_empty_by_default(self, container):
        """Should have empty notification senders by default."""
        assert container.notification_senders == []

    def test_add_notification_sender(self, container):
        """Should add notification senders."""
        # Create a mock sender
        class MockSender:
            @property
            def channel_name(self) -> str:
                return "mock"

            async def send(self, notification) -> bool:
                return True

        container.add_notification_sender(MockSender)

        senders = container.notification_senders
        assert len(senders) == 1
        assert senders[0].channel_name == "mock"

    def test_fluent_configuration(self, container):
        """Should support fluent configuration."""
        result = (
            container.configure_task_repository(InMemoryTaskRepository)
            .configure_personal_task_repository(InMemoryTaskRepository)
            .configure_cache_repository(InMemoryCacheRepository)
        )

        assert result is container
        assert isinstance(container.task_repository, InMemoryTaskRepository)
        assert isinstance(container.personal_task_repository, InMemoryTaskRepository)
        assert isinstance(container.cache_repository, InMemoryCacheRepository)

    def test_reset_clears_all(self, container):
        """Should clear all configured instances on reset."""
        container.configure_task_repository(InMemoryTaskRepository)
        container.configure_cache_repository(InMemoryCacheRepository)

        # Access to create instances
        repo1 = container.task_repository

        container.reset()

        # Re-configure after reset
        container.configure_task_repository(InMemoryTaskRepository)
        repo2 = container.task_repository

        # Should be different instances
        assert repo1 is not repo2

    def test_settings_lazy_load(self, container):
        """Should lazy load settings."""
        settings = container.settings
        assert settings is not None
        # Second access should return same instance
        assert container.settings is settings


class TestGlobalContainer:
    """Tests for global container functions."""

    def setup_method(self):
        """Reset container before each test."""
        reset_container()

    def test_get_container_returns_global(self):
        """Should return global container instance."""
        c1 = get_container()
        c2 = get_container()
        assert c1 is c2

    def test_reset_container_creates_new(self):
        """Should create new container on reset."""
        c1 = get_container()
        c1.configure_task_repository(InMemoryTaskRepository)

        reset_container()

        c2 = get_container()
        # New container should be unconfigured
        with pytest.raises(RuntimeError):
            _ = c2.task_repository
