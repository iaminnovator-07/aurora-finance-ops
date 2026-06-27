"""File storage abstraction (local + Supabase)."""

import hashlib
import uuid
from pathlib import Path

import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import NotFoundError, ProcessingError


class StorageService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self._supabase_client = None

    def _ensure_local_dir(self, subdir: str = "") -> Path:
        base = Path(self.settings.local_storage_path)
        target = base / subdir if subdir else base
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _get_supabase(self):
        if self._supabase_client is None:
            if not self.settings.supabase_url or not self.settings.supabase_key:
                raise ProcessingError(
                    "Supabase not configured",
                    reason="supabase_url and supabase_key are required for supabase backend",
                )
            from supabase import create_client

            self._supabase_client = create_client(
                self.settings.supabase_url, self.settings.supabase_key
            )
        return self._supabase_client

    async def save_file(
        self,
        content: bytes,
        filename: str,
        subdir: str = "documents",
    ) -> str:
        safe_name = f"{uuid.uuid4().hex}_{Path(filename).name}"
        if self.settings.storage_backend == "supabase":
            storage_path = f"{subdir}/{safe_name}"
            client = self._get_supabase()
            bucket = self.settings.supabase_bucket
            client.storage.from_(bucket).upload(storage_path, content)
            return f"supabase://{bucket}/{storage_path}"

        local_dir = self._ensure_local_dir(subdir)
        file_path = local_dir / safe_name
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        return str(file_path.resolve())

    def get_file_path(self, storage_path: str) -> Path:
        if storage_path.startswith("supabase://"):
            raise ProcessingError(
                "Cannot resolve Supabase path to local file",
                reason="Use read_file_bytes for supabase-stored files",
            )
        path = Path(storage_path)
        if not path.exists():
            raise NotFoundError("File", storage_path)
        return path

    async def read_file_bytes(self, storage_path: str) -> bytes:
        if storage_path.startswith("supabase://"):
            # supabase://bucket/subdir/file
            parts = storage_path.replace("supabase://", "").split("/", 1)
            if len(parts) != 2:
                raise ProcessingError(
                    "Invalid supabase storage path",
                    reason=f"Malformed path: {storage_path}",
                )
            bucket, object_path = parts
            client = self._get_supabase()
            return client.storage.from_(bucket).download(object_path)

        path = self.get_file_path(storage_path)
        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    @staticmethod
    def compute_checksum(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()
