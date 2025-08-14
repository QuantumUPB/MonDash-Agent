from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List

T = TypeVar('T')

class BasePoller(ABC, Generic[T]):
    """Abstract base class for poller implementations."""

    @abstractmethod
    async def poll(self) -> List[T]:
        """Poll external services and return collected results."""
        raise NotImplementedError
