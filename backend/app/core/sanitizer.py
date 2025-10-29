"""Input sanitization and validation for security."""
import re
import hashlib
from typing import Any, Optional
from pathlib import Path
import html


class InputSanitizer:
    """Comprehensive input sanitization to prevent injection attacks."""
    
    # Dangerous patterns to remove
    SCRIPT_PATTERN = re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL)
    HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
    SQL_INJECTION_PATTERN = re.compile(
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        re.IGNORECASE
    )
    PATH_TRAVERSAL_PATTERN = re.compile(r'\.\.[/\\]')
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 10000, allow_html: bool = False) -> str:
        """
        Sanitize text input.
        
        Args:
            text: Input text to sanitize
            max_length: Maximum allowed length
            allow_html: Whether to allow HTML tags
            
        Returns:
            Sanitized text
        """
        if not isinstance(text, str):
            text = str(text)
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove control characters except newline, tab, carriage return
        text = ''.join(char for char in text if char in '\n\r\t' or ord(char) >= 32)
        
        # Limit length
        text = text[:max_length]
        
        # Remove script tags
        text = InputSanitizer.SCRIPT_PATTERN.sub('', text)
        
        # Remove HTML tags if not allowed
        if not allow_html:
            text = InputSanitizer.HTML_TAG_PATTERN.sub('', text)
            text = html.unescape(text)  # Decode HTML entities
        
        # Remove potential SQL injection attempts
        text = InputSanitizer.SQL_INJECTION_PATTERN.sub('', text)
        
        return text.strip()
    
    @staticmethod
    def sanitize_filename(filename: str, max_length: int = 255) -> str:
        """
        Sanitize filename to prevent path traversal and invalid characters.
        
        Args:
            filename: Input filename
            max_length: Maximum filename length
            
        Returns:
            Sanitized filename
        """
        if not isinstance(filename, str):
            filename = str(filename)
        
        # Remove path traversal attempts
        filename = InputSanitizer.PATH_TRAVERSAL_PATTERN.sub('', filename)
        
        # Remove path separators
        filename = filename.replace('/', '').replace('\\', '')
        
        # Allow only alphanumeric, dash, underscore, and period
        filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)
        
        # Ensure it doesn't start with a period (hidden files)
        if filename.startswith('.'):
            filename = '_' + filename[1:]
        
        # Limit length
        if len(filename) > max_length:
            # Keep extension if present
            parts = filename.rsplit('.', 1)
            if len(parts) == 2:
                name, ext = parts
                filename = name[:max_length - len(ext) - 1] + '.' + ext
            else:
                filename = filename[:max_length]
        
        return filename or 'unnamed'
    
    @staticmethod
    def sanitize_path(path: str, base_dir: Optional[str] = None) -> Path:
        """
        Sanitize file path and ensure it's within base directory.
        
        Args:
            path: Input path
            base_dir: Base directory to constrain path to
            
        Returns:
            Sanitized Path object
            
        Raises:
            ValueError: If path tries to escape base directory
        """
        # Resolve path
        clean_path = Path(path).resolve()
        
        # Check if within base directory
        if base_dir:
            base_path = Path(base_dir).resolve()
            try:
                clean_path.relative_to(base_path)
            except ValueError:
                raise ValueError(f"Path {path} is outside base directory {base_dir}")
        
        return clean_path
    
    @staticmethod
    def validate_session_id(session_id: str) -> bool:
        """
        Validate session ID format (UUID).
        
        Args:
            session_id: Session ID to validate
            
        Returns:
            True if valid, False otherwise
        """
        # UUID v4 pattern
        uuid_pattern = re.compile(
            r'^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$',
            re.IGNORECASE
        )
        return bool(uuid_pattern.match(session_id))
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email format.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid, False otherwise
        """
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        return bool(email_pattern.match(email))
    
    @staticmethod
    def sanitize_url(url: str, allowed_schemes: Optional[list] = None) -> str:
        """
        Sanitize URL and validate scheme.
        
        Args:
            url: URL to sanitize
            allowed_schemes: List of allowed URL schemes (default: ['http', 'https'])
            
        Returns:
            Sanitized URL
            
        Raises:
            ValueError: If URL scheme is not allowed
        """
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
        
        url = url.strip()
        
        # Check scheme
        if '://' in url:
            scheme = url.split('://')[0].lower()
            if scheme not in allowed_schemes:
                raise ValueError(f"URL scheme '{scheme}' not allowed")
        
        # Remove javascript: and data: URIs
        if url.lower().startswith(('javascript:', 'data:', 'vbscript:')):
            raise ValueError("Potentially dangerous URL scheme")
        
        return url
    
    @staticmethod
    def hash_content(content: str) -> str:
        """
        Create SHA-256 hash of content.
        
        Args:
            content: Content to hash
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    @staticmethod
    def validate_json_safe(data: Any, max_depth: int = 10, current_depth: int = 0) -> bool:
        """
        Validate that data structure is safe for JSON serialization.
        
        Args:
            data: Data to validate
            max_depth: Maximum nesting depth
            current_depth: Current depth (internal use)
            
        Returns:
            True if safe, False otherwise
        """
        if current_depth > max_depth:
            return False
        
        if isinstance(data, (str, int, float, bool, type(None))):
            return True
        elif isinstance(data, dict):
            return all(
                isinstance(k, str) and 
                InputSanitizer.validate_json_safe(v, max_depth, current_depth + 1)
                for k, v in data.items()
            )
        elif isinstance(data, (list, tuple)):
            return all(
                InputSanitizer.validate_json_safe(item, max_depth, current_depth + 1)
                for item in data
            )
        else:
            return False
    
    @staticmethod
    def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
        """
        Truncate text to maximum length with suffix.
        
        Args:
            text: Text to truncate
            max_length: Maximum length
            suffix: Suffix to add if truncated
            
        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def remove_sensitive_data(text: str) -> str:
        """
        Remove potentially sensitive data patterns from text.
        
        Args:
            text: Text to clean
            
        Returns:
            Text with sensitive data masked
        """
        # Mask credit card numbers
        text = re.sub(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', '[CARD]', text)
        
        # Mask email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        
        # Mask phone numbers
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
        
        # Mask SSN
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
        
        # Mask API keys (common patterns)
        text = re.sub(r'\b[A-Za-z0-9]{32,}\b', '[API_KEY]', text)
        
        return text


# Convenience instance
sanitizer = InputSanitizer()
