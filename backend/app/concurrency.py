import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from functools import TimeoutError as FuturesTimeoutError
from typing import Any, Callable, Optional


class ConcurrencyManager:
    """
    并发控制管理器
    - 隔离重型操作（LLM/Embedding）到专用线程池
    - 信号量限制最大并发，超出则立即返回 503
    - 互斥锁防止重复索引
    """

    _instance: Optional["ConcurrencyManager"] = None

    def __init__(
        self,
        max_workers: int,
        max_concurrent_chat: int,
        chat_timeout: int,
        index_timeout: int,
    ) -> None:
        self.max_workers = max_workers
        self.max_concurrent_chat = max_concurrent_chat
        self.chat_timeout = chat_timeout
        self.index_timeout = index_timeout

        self._chat_semaphore = asyncio.Semaphore(max_concurrent_chat)
        self._index_lock = asyncio.Lock()
        self._indexing = False

        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="rag-worker",
        )

    @classmethod
    def create(
        cls,
        max_workers: int = None,
        max_concurrent_chat: int = None,
        chat_timeout: int = None,
        index_timeout: int = None,
    ) -> "ConcurrencyManager":
        cpu_count = os.cpu_count() or 4
        if max_workers is None:
            max_workers = min(cpu_count, 8)
        if max_concurrent_chat is None:
            max_concurrent_chat = max_workers
        if chat_timeout is None:
            chat_timeout = 120
        if index_timeout is None:
            index_timeout = 600
        if cls._instance is None:
            cls._instance = cls(
                max_workers=max_workers,
                max_concurrent_chat=max_concurrent_chat,
                chat_timeout=chat_timeout,
                index_timeout=index_timeout,
            )
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ConcurrencyManager":
        if cls._instance is None:
            raise RuntimeError("ConcurrencyManager not initialized")
        return cls._instance

    async def run_chat(
        self,
        func: Callable[..., Any],
        *args, **kwargs
    ) -> Any:
        """
        带并发控制的 chat 执行器
        - 信号量控制并发上限
        - 超时控制
        - 专用线程池隔离
        """
        loop = asyncio.get_running_loop()

        try:
            acquired = await asyncio.wait_for(
                self._chat_semaphore.acquire(), timeout=0
            )
        except asyncio.TimeoutError:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=503,
                detail=(
                    f"服务器繁忙，当前最大并发数 {self.max_concurrent_chat} "
                    "已全部占用，请稍后再试"
                ),
            )

        try:
            future = loop.run_in_executor(
                self._executor, lambda: func(*args, **kwargs)
            )
            return await asyncio.wait_for(future, timeout=self.chat_timeout)
        except asyncio.TimeoutError:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=504,
                detail=f"请求处理超时（超过 {self.chat_timeout} 秒）",
            )
        except FuturesTimeoutError:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=504,
                detail=f"请求处理超时（超过 {self.chat_timeout} 秒）",
            )
        finally:
            if acquired:
                self._chat_semaphore.release()

    async def run_index(
        self,
        func: Callable[..., Any],
        *args, **kwargs
    ) -> Any:
        """
        带互斥锁的 index 执行器
        - 同一时间只允许一个索引任务
        - 专用线程池隔离
        """
        loop = asyncio.get_running_loop()

        from fastapi import HTTPException

        if self._index_lock.locked():
            raise HTTPException(
                status_code=409,
                detail="当前正在执行索引任务，请稍后再试",
            )

        async with self._index_lock:
            self._indexing = True
            try:
                future = loop.run_in_executor(
                    self._executor, lambda: func(*args, **kwargs)
                )
                return await asyncio.wait_for(future, timeout=self.index_timeout)
            except asyncio.TimeoutError:
                raise HTTPException(
                    status_code=504,
                    detail=f"索引超时（超过 {self.index_timeout} 秒）",
                )
            except FuturesTimeoutError:
                raise HTTPException(
                    status_code=504,
                    detail=f"索引超时（超过 {self.index_timeout} 秒）",
                )
            finally:
                self._indexing = False

    def is_indexing(self) -> bool:
        return self._indexing

    def get_stats(self) -> dict:
        return {
            "max_workers": self.max_workers,
            "max_concurrent_chat": self.max_concurrent_chat,
            "chat_timeout": self.chat_timeout,
            "index_timeout": self.index_timeout,
            "is_indexing": self._indexing,
            "chat_active_count": (
                self.max_concurrent_chat - self._chat_semaphore._value
            ),
        }

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)
