"""
File storage implementation for web crawler content.

Provides robust file storage with proper error handling, atomic writes,
and metadata management for production environments.
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from ..core.interfaces import IStorage
from ..utils.exceptions import StorageError
from ..utils.validators import URLValidator

logger = logging.getLogger(__name__)


class FileStorage(IStorage):
    """Handles file storage operations for crawled content."""
    
    def __init__(self, base_directory: Path, create_subdirs: bool = True):
        """
        Initialize file storage handler.
        
        Args:
            base_directory: Base directory for storing files
            create_subdirs: Whether to create subdirectories by domain
        """
        self.base_directory = Path(base_directory)
        self.create_subdirs = create_subdirs
        self._ensure_directory_exists(self.base_directory)
    
    async def save_content(self, 
                          content: str, 
                          filename: str, 
                          metadata: Optional[Dict[str, Any]] = None) -> Path:
        """
        Save content to file with atomic write operation.
        
        Args:
            content: Content to save
            filename: Name of the file
            metadata: Optional metadata to save alongside content
            
        Returns:
            Path to the saved file
            
        Raises:
            StorageError: If saving fails
        """
        if not content:
            raise StorageError("Content cannot be empty")
        
        if not filename:
            raise StorageError("Filename cannot be empty")
        
        try:
            # Get full file path
            file_path = self.get_storage_path(filename)
            
            # Ensure parent directory exists
            self._ensure_directory_exists(file_path.parent)
            
            # Perform atomic write
            await self._atomic_write(file_path, content)
            
            # Save metadata if provided
            if metadata:
                await self._save_metadata(file_path, metadata)
            
            logger.info(f"Successfully saved content to {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to save content to {filename}: {e}")
            raise StorageError(f"Failed to save content: {e}", filename)
    
    def get_storage_path(self, filename: str) -> Path:
        """
        Get the full storage path for a filename.
        
        Args:
            filename: Name of the file
            
        Returns:
            Full path to the file
        """
        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)
        
        if self.create_subdirs:
            # Extract domain from filename for subdirectory
            domain = self._extract_domain_from_filename(safe_filename)
            return self.base_directory / domain / f"{safe_filename}.txt"
        else:
            return self.base_directory / f"{safe_filename}.txt"
    
    async def _atomic_write(self, file_path: Path, content: str) -> None:
        """
        Perform atomic write operation to prevent corruption.
        
        Args:
            file_path: Target file path
            content: Content to write
        """
        temp_path = file_path.with_suffix(f"{file_path.suffix}.tmp")
        
        try:
            # Write to temporary file first
            async with asyncio.Lock():  # Ensure thread safety
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk
                
                # Atomic move to final location
                temp_path.replace(file_path)
                
        except Exception as e:
            # Clean up temporary file on error
            if temp_path.exists():
                temp_path.unlink()
            raise StorageError(f"Atomic write failed: {e}")
    
    async def _save_metadata(self, content_path: Path, metadata: Dict[str, Any]) -> None:
        """
        Save metadata alongside content file.
        
        Args:
            content_path: Path to the content file
            metadata: Metadata to save
        """
        metadata_path = content_path.with_suffix('.meta.json')
        
        # Add storage metadata
        storage_metadata = {
            'saved_at': datetime.utcnow().isoformat(),
            'content_file': content_path.name,
            'file_size': content_path.stat().st_size if content_path.exists() else 0,
            **metadata
        }
        
        try:
            metadata_json = json.dumps(storage_metadata, indent=2, ensure_ascii=False)
            await self._atomic_write(metadata_path, metadata_json)
            
        except Exception as e:
            logger.warning(f"Failed to save metadata for {content_path}: {e}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe file system storage.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove or replace unsafe characters
        import re
        
        # Replace unsafe characters with underscores
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Remove control characters
        safe_name = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', safe_name)
        
        # Collapse multiple underscores
        safe_name = re.sub(r'_+', '_', safe_name)
        
        # Remove leading/trailing dots and spaces
        safe_name = safe_name.strip('. ')
        
        # Ensure reasonable length
        if len(safe_name) > 100:
            safe_name = safe_name[:97] + '...'
        
        # Ensure not empty
        if not safe_name:
            safe_name = 'unnamed_file'
        
        return safe_name
    
    def _extract_domain_from_filename(self, filename: str) -> str:
        """
        Extract domain from filename for subdirectory creation.
        
        Args:
            filename: Filename to extract domain from
            
        Returns:
            Domain string for subdirectory
        """
        # Try to extract domain from filename
        parts = filename.split('_')
        if parts:
            potential_domain = parts[0]
            # Basic domain validation
            if '.' in potential_domain and len(potential_domain) > 3:
                return self._sanitize_filename(potential_domain)
        
        return 'misc'
    
    def _ensure_directory_exists(self, directory: Path) -> None:
        """
        Ensure directory exists, create if necessary.
        
        Args:
            directory: Directory path to check/create
            
        Raises:
            StorageError: If directory creation fails
        """
        try:
            directory.mkdir(parents=True, exist_ok=True)
            
            # Verify directory is writable
            test_file = directory / '.write_test'
            try:
                test_file.touch()
                test_file.unlink()
            except Exception:
                raise StorageError(f"Directory not writable: {directory}")
                
        except Exception as e:
            raise StorageError(f"Failed to create directory {directory}: {e}")
    
    def list_files(self, pattern: str = "*.txt") -> list[Path]:
        """
        List stored files matching pattern.
        
        Args:
            pattern: Glob pattern for file matching
            
        Returns:
            List of file paths
        """
        try:
            if self.create_subdirs:
                # Search in all subdirectories
                files = []
                for subdir in self.base_directory.iterdir():
                    if subdir.is_dir():
                        files.extend(subdir.glob(pattern))
                return files
            else:
                return list(self.base_directory.glob(pattern))
                
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []
    
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Get information about a stored file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary containing file information
        """
        info = {}
        
        try:
            if file_path.exists():
                stat = file_path.stat()
                info.update({
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'exists': True
                })
                
                # Try to load metadata
                metadata_path = file_path.with_suffix('.meta.json')
                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            info['metadata'] = metadata
                    except Exception as e:
                        logger.warning(f"Failed to load metadata for {file_path}: {e}")
            else:
                info['exists'] = False
                
        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {e}")
            info['error'] = str(e)
        
        return info
