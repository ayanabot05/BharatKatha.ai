"""The cross-origin MP4 link must receive an attachment response."""
import asyncio
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
import server


def test_media_download_header_is_opt_in_and_preview_stays_inline():
    async def check():
        with patch.object(server, "db") as database, \
             patch.object(server, "get_object", new=AsyncMock(return_value=(b"mp4", "video/mp4"))):
            database.files.find_one = AsyncMock(return_value={"content_type": "video/mp4"})
            user = {"id": "creator"}
            path = "creator/videos/render-1.mp4"
            preview = await server.media(path, download=False, user=user)
            saved = await server.media(path, download=True, user=user)

        assert preview.media_type == saved.media_type == "video/mp4"
        assert preview.body == saved.body == b"mp4"
        assert "content-disposition" not in preview.headers
        assert saved.headers["content-disposition"] == 'attachment; filename="render-1.mp4"'
        database.files.find_one.assert_awaited_with(
            {"storage_path": path, "user_id": "creator", "is_deleted": False})

    asyncio.run(check())


def test_media_for_another_user_is_not_read_from_storage():
    async def check():
        with patch.object(server, "db") as database, \
             patch.object(server, "get_object", new=AsyncMock()) as storage:
            database.files.find_one = AsyncMock(return_value=None)
            try:
                await server.media("private/videos/another-user.mp4", user={"id": "viewer"})
                assert False, "Expected ownership rejection"
            except HTTPException as error:
                assert error.status_code == 404
            storage.assert_not_awaited()
            database.files.find_one.assert_awaited_once_with({
                "storage_path": "private/videos/another-user.mp4",
                "user_id": "viewer", "is_deleted": False,
            })

    asyncio.run(check())
