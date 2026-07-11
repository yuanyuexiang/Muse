from pathlib import Path
from typing import Protocol

from app.config import settings


class Storage(Protocol):
    """存储抽象：Phase 1 用本地卷，切 MinIO/S3 只换实现，上层不变。"""

    def save(self, key: str, data: bytes, content_type: str | None = None) -> str: ...

    def load(self, key: str) -> bytes: ...


class LocalStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, key: str, data: bytes, content_type: str | None = None) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def load(self, key: str) -> bytes:
        return (self.root / key).read_bytes()


class MinioStorage:
    """TODO(Phase 1 可选)：用 minio SDK 实现；STORAGE_BACKEND=minio 时启用。"""

    def __init__(self) -> None:
        raise NotImplementedError("MinIO 存储待接入；当前用 STORAGE_BACKEND=local")

    def save(self, key: str, data: bytes, content_type: str | None = None) -> str:  # pragma: no cover
        raise NotImplementedError

    def load(self, key: str) -> bytes:  # pragma: no cover
        raise NotImplementedError


def get_storage() -> Storage:
    if settings.storage_backend == "minio":
        return MinioStorage()
    return LocalStorage(settings.storage_dir)


storage: Storage = get_storage()
