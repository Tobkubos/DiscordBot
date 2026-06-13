import logging
import httpx

from app.core.config import get_settings
from app.utils.exceptions import (
    FileDownloadError,
    InvalidURLError,
    DownloadTimeoutError,
    FileSizeError,
)

logger = logging.getLogger(__name__)


async def download_file(file_url: str) -> bytes:
    """
    Asynchronously download a file from the given URL.
    
    Args:
        file_url: The URL of the file to download
        
    Returns:
        The file contents as bytes
        
    Raises:
        InvalidURLError: If the URL is invalid
        DownloadTimeoutError: If download times out
        FileSizeError: If file size exceeds limit
        FileDownloadError: If download fails for other reasons
    """
    settings = get_settings()
    logger.info(f"Starting file download from: {file_url}")
    
    try:
        async with httpx.AsyncClient(timeout=settings.DOWNLOAD_TIMEOUT) as client:
            response = await client.get(file_url, follow_redirects=True)
            
            # Check for HTTP errors
            if response.status_code != 200:
                logger.error(
                    f"Failed to download file. Status code: {response.status_code}"
                )
                raise FileDownloadError(
                    f"Failed to download file. Server returned status code {response.status_code}",
                    status_code=response.status_code,
                )
            
            # Check content length header
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > settings.MAX_FILE_SIZE:
                logger.error(
                    f"File size exceeds maximum allowed size: {content_length} bytes"
                )
                raise FileSizeError(
                    f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE} bytes"
                )
            
            file_bytes = response.content
            
            # Check actual content size
            if len(file_bytes) > settings.MAX_FILE_SIZE:
                logger.error(
                    f"Downloaded file exceeds maximum size: {len(file_bytes)} bytes"
                )
                raise FileSizeError(
                    f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE} bytes"
                )
            
            logger.info(
                f"File download completed successfully. Size: {len(file_bytes)} bytes"
            )
            return file_bytes
            
    except httpx.InvalidURL as e:
        logger.error(f"Invalid URL provided: {file_url} - {str(e)}")
        raise InvalidURLError("Invalid URL format")
    except httpx.TimeoutException as e:
        logger.error(f"Download timeout for URL: {file_url}")
        raise DownloadTimeoutError("File download timed out. Please try again with a faster source.")
    except (FileSizeError, InvalidURLError, DownloadTimeoutError):
        # Re-raise custom exceptions
        raise
    except httpx.RequestError as e:
        logger.error(f"Failed to download file from {file_url}: {str(e)}")
        raise FileDownloadError(
            "Failed to download file from the provided URL. Please check the URL and try again."
        )
    except Exception as e:
        logger.error(f"Unexpected error during file download: {str(e)}")
        raise FileDownloadError(
            "An unexpected error occurred during file download."
        )
