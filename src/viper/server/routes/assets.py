"""Asset file streaming API endpoints."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from viper.config import VIPER_MEDIA_DIR

router = APIRouter(prefix='/api/assets', tags=['assets'])


@router.get('/{asset_path:path}')
async def stream_asset(asset_path: str) -> FileResponse:
    """Stream generated media assets preventing directory traversal."""
    base_dir = VIPER_MEDIA_DIR.resolve()

    # Normalize candidate paths with or without data/media prefix
    candidates: list[Path] = [
        (base_dir / asset_path).resolve(),
    ]

    cleaned = asset_path.lstrip('/')
    if cleaned.startswith('data/media/'):
        prefix = 'data/media/'
        candidates.append((base_dir / cleaned.removeprefix(prefix)).resolve())
    elif cleaned.startswith('media/'):
        prefix = 'media/'
        candidates.append((base_dir / cleaned.removeprefix(prefix)).resolve())

    # Fallback to filename inside base_dir
    filename = Path(asset_path).name
    if filename:
        candidates.append((base_dir / filename).resolve())

    for target_file in candidates:
        if not target_file.is_relative_to(base_dir):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Access forbidden: path traversal detected',
            )

        if target_file.exists() and target_file.is_file():
            return FileResponse(target_file)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Asset '{asset_path}' not found",
    )
