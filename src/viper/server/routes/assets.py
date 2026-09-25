"""Asset file streaming API endpoints."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from viper.config import VIPER_MEDIA_DIR

router = APIRouter(prefix='/api/assets', tags=['assets'])


@router.get('/{asset_path:path}')
async def stream_asset(asset_path: str) -> FileResponse:
    """Stream generated media assets preventing directory traversal."""
    base_dir = VIPER_MEDIA_DIR.resolve()
    target_file = (base_dir / asset_path).resolve()

    if not target_file.is_relative_to(base_dir):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access forbidden: path traversal detected',
        )

    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_path}' not found",
        )

    return FileResponse(target_file)
