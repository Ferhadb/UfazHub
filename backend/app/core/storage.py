"""Storage interface for uploaded files. LocalStorage writes under MEDIA_ROOT.

S3-ready: an S3 backend only has to implement these four coroutines and be returned by
`get_storage()`; nothing else in the app touches the filesystem.
"""

import asyncio
from pathlib import Path
from typing import Protocol

from app.core.config import settings


class Storage(Protocol):
    async def put(self, key: str, data: bytes) -> None: ...
    async def get(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...
    async def exists(self, key: str) -> bool: ...


class LocalStorage:
    def __init__(self, root: str):
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(
            self.root
        ):  # keys never come from users, but be sure
            raise ValueError("storage key escapes MEDIA_ROOT")
        return path

    async def put(self, key: str, data: bytes) -> None:
        def write() -> None:
            path = self._path(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + ".part")
            tmp.write_bytes(data)
            tmp.replace(path)  # readers never see a half-written file

        await asyncio.to_thread(write)

    async def get(self, key: str) -> bytes:
        return await asyncio.to_thread(self._path(key).read_bytes)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._path(key).unlink, True)

    async def exists(self, key: str) -> bool:
        return await asyncio.to_thread(self._path(key).is_file)


def get_storage() -> Storage:
    return LocalStorage(settings.MEDIA_ROOT)
