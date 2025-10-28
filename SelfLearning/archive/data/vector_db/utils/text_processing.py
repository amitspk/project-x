"""
Text processing utilities for the vector database module.

This module provides utilities for preprocessing text content before
embedding generation and chunking large documents for processing.
"""

import re
import html
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class ChunkingConfig:
    """Configuration for text chunking operations."""
    
    chunk_size: int = 1000  # Maximum characters per chunk
    chunk_overlap: int = 100  # Overlap between consecutive chunks
    respect_sentences: bool = True  # Try to break at sentence boundaries
    respect_paragraphs: bool = True  # Try to break at paragraph boundaries
    min_chunk_size: int = 50  # Minimum characters per chunk
    max_chunk_size: int = 2000  # Maximum characters per chunk


class TextPreprocessor:
    """
    Text preprocessing utilities for cleaning and normalizing content.
    
    Provides methods for cleaning HTML, normalizing whitespace,
    removing unwanted characters, and preparing text for embedding.
    """
    
    def __init__(self):
        """Initialize text preprocessor."""
        # Compile regex patterns for efficiency
        self._html_tag_pattern = re.compile(r'<[^>]+>')
        self._whitespace_pattern = re.compile(r'\s+')
        self._url_pattern = re.compile(r'https?://[^\s]+')
        self._email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self._special_chars_pattern = re.compile(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\{\}\"\']+')
    
    def clean_html(self, text: str) -> str:
        """
        Remove HTML tags and decode HTML entities.
        
        Args:
            text: Text containing HTML
            
        Returns:
            Cleaned text without HTML tags
        """
        # Decode HTML entities
        text = html.unescape(text)
        
        # Remove HTML tags
        text = self._html_tag_pattern.sub(' ', text)
        
        return text
    
    def normalize_whitespace(self, text: str) -> str:
        """
        Normalize whitespace by replacing multiple spaces with single space.
        
        Args:
            text: Text with irregular whitespace
            
        Returns:
            Text with normalized whitespace
        """
        return self._whitespace_pattern.sub(' ', text).strip()
    
    def remove_urls(self, text: str, replacement: str = '[URL]') -> str:
        """
        Remove or replace URLs in text.
        
        Args:
            text: Text containing URLs
            replacement: String to replace URLs with
            
        Returns:
            Text with URLs removed or replaced
        """
        return self._url_pattern.sub(replacement, text)
    
    def remove_emails(self, text: str, replacement: str = '[EMAIL]') -> str:
        """
        Remove or replace email addresses in text.
        
        Args:
            text: Text containing email addresses
            replacement: String to replace emails with
            
        Returns:
            Text with emails removed or replaced
        """
        return self._email_pattern.sub(replacement, text)
    
    def remove_special_characters(self, text: str, keep_punctuation: bool = True) -> str:
        """
        Remove special characters while optionally keeping punctuation.
        
        Args:
            text: Text containing special characters
            keep_punctuation: Whether to keep basic punctuation
            
        Returns:
            Text with special characters removed
        """
        if keep_punctuation:
            return self._special_chars_pattern.sub(' ', text)
        else:
            # Remove all non-alphanumeric characters except spaces
            return re.sub(r'[^\w\s]', ' ', text)
    
    def preprocess(
        self,
        text: str,
        clean_html: bool = True,
        normalize_whitespace: bool = True,
        remove_urls: bool = False,
        remove_emails: bool = False,
        remove_special_chars: bool = False,
        keep_punctuation: bool = True,
        min_length: int = 10
    ) -> str:
        """
        Apply comprehensive text preprocessing.
        
        Args:
            text: Raw text to preprocess
            clean_html: Whether to remove HTML tags
            normalize_whitespace: Whether to normalize whitespace
            remove_urls: Whether to remove URLs
            remove_emails: Whether to remove email addresses
            remove_special_chars: Whether to remove special characters
            keep_punctuation: Whether to keep punctuation (if removing special chars)
            min_length: Minimum length of processed text
            
        Returns:
            Preprocessed text
            
        Raises:
            ValueError: If processed text is too short
        """
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty")
        
        processed_text = text
        
        if clean_html:
            processed_text = self.clean_html(processed_text)
        
        if remove_urls:
            processed_text = self.remove_urls(processed_text)
        
        if remove_emails:
            processed_text = self.remove_emails(processed_text)
        
        if remove_special_chars:
            processed_text = self.remove_special_characters(
                processed_text, keep_punctuation
            )
        
        if normalize_whitespace:
            processed_text = self.normalize_whitespace(processed_text)
        
        if len(processed_text) < min_length:
            raise ValueError(f"Processed text too short: {len(processed_text)} < {min_length}")
        
        return processed_text


class TextChunker:
    """
    Text chunking utilities for splitting large documents into smaller pieces.
    
    Provides intelligent chunking that respects sentence and paragraph boundaries
    while maintaining configurable chunk sizes and overlaps.
    """
    
    def __init__(self, config: Optional[ChunkingConfig] = None):
        """
        Initialize text chunker.
        
        Args:
            config: Chunking configuration
        """
        self.config = config or ChunkingConfig()
        
        # Compile regex patterns for sentence and paragraph detection
        self._sentence_pattern = re.compile(r'[.!?]+\s+')
        self._paragraph_pattern = re.compile(r'\n\s*\n')
    
    def chunk_by_characters(self, text: str) -> List[str]:
        """
        Split text into chunks by character count with overlap.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        if len(text) <= self.config.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + self.config.chunk_size, len(text))
            chunk = text[start:end]
            
            # Ensure minimum chunk size
            if len(chunk) >= self.config.min_chunk_size:
                chunks.append(chunk)
            
            if end >= len(text):
                break
            
            start = end - self.config.chunk_overlap
        
        return chunks
    
    def chunk_by_sentences(self, text: str) -> List[str]:
        """
        Split text into chunks respecting sentence boundaries.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        # Split into sentences
        sentences = self._sentence_pattern.split(text)
        if not sentences:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if adding this sentence would exceed chunk size
            potential_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(potential_chunk) <= self.config.chunk_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk if it meets minimum size
                if current_chunk and len(current_chunk) >= self.config.min_chunk_size:
                    chunks.append(current_chunk)
                
                # Start new chunk with current sentence
                current_chunk = sentence
        
        # Add final chunk
        if current_chunk and len(current_chunk) >= self.config.min_chunk_size:
            chunks.append(current_chunk)
        
        return self._add_overlap(chunks)
    
    def chunk_by_paragraphs(self, text: str) -> List[str]:
        """
        Split text into chunks respecting paragraph boundaries.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        # Split into paragraphs
        paragraphs = self._paragraph_pattern.split(text)
        if not paragraphs:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # Check if adding this paragraph would exceed chunk size
            potential_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
            
            if len(potential_chunk) <= self.config.chunk_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk if it meets minimum size
                if current_chunk and len(current_chunk) >= self.config.min_chunk_size:
                    chunks.append(current_chunk)
                
                # If paragraph is too large, split it by sentences
                if len(paragraph) > self.config.chunk_size:
                    paragraph_chunks = self.chunk_by_sentences(paragraph)
                    chunks.extend(paragraph_chunks)
                    current_chunk = ""
                else:
                    current_chunk = paragraph
        
        # Add final chunk
        if current_chunk and len(current_chunk) >= self.config.min_chunk_size:
            chunks.append(current_chunk)
        
        return self._add_overlap(chunks)
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks using the configured strategy.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []
        
        # Choose chunking strategy based on configuration
        if self.config.respect_paragraphs:
            chunks = self.chunk_by_paragraphs(text)
        elif self.config.respect_sentences:
            chunks = self.chunk_by_sentences(text)
        else:
            chunks = self.chunk_by_characters(text)
        
        # Filter chunks by size constraints
        filtered_chunks = []
        for chunk in chunks:
            if self.config.min_chunk_size <= len(chunk) <= self.config.max_chunk_size:
                filtered_chunks.append(chunk)
        
        return filtered_chunks
    
    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """
        Add overlap between consecutive chunks.
        
        Args:
            chunks: List of chunks without overlap
            
        Returns:
            List of chunks with overlap added
        """
        if len(chunks) <= 1 or self.config.chunk_overlap <= 0:
            return chunks
        
        overlapped_chunks = [chunks[0]]  # First chunk remains unchanged
        
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            current_chunk = chunks[i]
            
            # Extract overlap from previous chunk
            overlap_text = prev_chunk[-self.config.chunk_overlap:] if len(prev_chunk) > self.config.chunk_overlap else prev_chunk
            
            # Add overlap to current chunk
            overlapped_chunk = overlap_text + " " + current_chunk
            overlapped_chunks.append(overlapped_chunk)
        
        return overlapped_chunks
    
    def get_chunk_metadata(self, chunks: List[str], original_text: str) -> List[Dict[str, Any]]:
        """
        Generate metadata for each chunk.
        
        Args:
            chunks: List of text chunks
            original_text: Original text before chunking
            
        Returns:
            List of metadata dictionaries for each chunk
        """
        metadata_list = []
        
        for i, chunk in enumerate(chunks):
            metadata = {
                'chunk_index': i,
                'chunk_count': len(chunks),
                'chunk_size': len(chunk),
                'word_count': len(chunk.split()),
                'character_count': len(chunk),
                'start_position': original_text.find(chunk) if chunk in original_text else -1,
                'overlap_size': self.config.chunk_overlap if i > 0 else 0
            }
            metadata_list.append(metadata)
        
        return metadata_list
