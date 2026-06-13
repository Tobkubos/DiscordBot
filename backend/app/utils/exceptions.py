"""Custom exception classes."""


class DeepfakeDetectionError(Exception):
    """Base exception for deepfake detection service."""
    
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class FileDownloadError(DeepfakeDetectionError):
    """Exception raised when file download fails."""
    
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, status_code)


class InvalidURLError(DeepfakeDetectionError):
    """Exception raised when URL is invalid."""
    
    def __init__(self, message: str = "Invalid URL format"):
        super().__init__(message, 400)


class DownloadTimeoutError(DeepfakeDetectionError):
    """Exception raised when file download times out."""
    
    def __init__(self, message: str = "File download timed out"):
        super().__init__(message, 408)


class FileSizeError(DeepfakeDetectionError):
    """Exception raised when file size exceeds limit."""
    
    def __init__(self, message: str = "File size exceeds maximum allowed size"):
        super().__init__(message, 400)


class DetectorError(DeepfakeDetectionError):
    """Exception raised when detector model fails."""
    
    def __init__(self, message: str = "Deepfake detection failed"):
        super().__init__(message, 500)


class UnsupportedModelError(DeepfakeDetectionError):
    """Exception raised when requested model is not supported."""
    
    def __init__(self, model_name: str):
        message = f"Detector model '{model_name}' is not supported"
        super().__init__(message, 400)
