"""
Simple test script to verify vector database module installation and basic functionality.

This script performs basic tests without requiring external API keys or dependencies.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


async def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        # Test core imports
        from vector_db import VectorSearchService, VectorMetadata, SearchResult
        from vector_db.core.interfaces import IEmbeddingProvider, IVectorStore
        from vector_db.models.vector_models import VectorDocument, EmbeddingRequest
        from vector_db.utils.exceptions import VectorDBError, EmbeddingError
        from vector_db.utils.text_processing import TextPreprocessor, TextChunker
        from vector_db.utils.similarity_metrics import cosine_similarity
        
        print("✓ Core imports successful")
        
        # Test service imports
        from vector_db.services.embedding_service import EmbeddingService
        from vector_db.services.vector_service import VectorSearchService
        from vector_db.storage.in_memory_store import InMemoryVectorStore
        
        print("✓ Service imports successful")
        
        # Test provider imports (these might fail if dependencies not installed)
        try:
            from vector_db.providers.openai_provider import OpenAIEmbeddingProvider
            print("✓ OpenAI provider import successful")
        except ImportError as e:
            print(f"⚠ OpenAI provider not available: {e}")
        
        try:
            from vector_db.providers.sentence_transformers_provider import SentenceTransformersProvider
            print("✓ Sentence Transformers provider import successful")
        except ImportError as e:
            print(f"⚠ Sentence Transformers provider not available: {e}")
        
        # Test integration imports
        try:
            from vector_content_processor import VectorContentProcessor
            print("✓ Vector content processor import successful")
        except ImportError as e:
            print(f"⚠ Vector content processor not available: {e}")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


async def test_basic_functionality():
    """Test basic functionality without external dependencies."""
    print("\nTesting basic functionality...")
    
    try:
        import numpy as np
        from vector_db.models.vector_models import VectorMetadata, VectorDocument
        from vector_db.storage.in_memory_store import InMemoryVectorStore
        from vector_db.utils.similarity_metrics import cosine_similarity
        from vector_db.utils.text_processing import TextPreprocessor, TextChunker
        
        # Test 1: Vector metadata creation
        metadata = VectorMetadata(
            title="Test Document",
            url="https://example.com/test",
            content_type="test",
            tags=["test", "example"],
            categories=["testing"]
        )
        assert metadata.title == "Test Document"
        assert "test" in metadata.tags
        print("✓ VectorMetadata creation works")
        
        # Test 2: Vector document creation
        test_embedding = np.random.rand(384).astype(np.float32)
        doc = VectorDocument(
            content="This is test content for the vector database.",
            embedding=test_embedding,
            metadata=metadata
        )
        assert doc.content == "This is test content for the vector database."
        assert doc.embedding.shape == (384,)
        print("✓ VectorDocument creation works")
        
        # Test 3: In-memory vector store
        store = InMemoryVectorStore(embedding_dimension=384)
        await store.initialize()
        
        # Add document
        doc_id = await store.add_document(doc)
        assert doc_id is not None
        print("✓ In-memory store add_document works")
        
        # Retrieve document
        retrieved_doc = await store.get_document(doc_id)
        assert retrieved_doc is not None
        assert retrieved_doc.content == doc.content
        print("✓ In-memory store get_document works")
        
        # Test similarity search
        query_embedding = np.random.rand(384).astype(np.float32)
        results = await store.similarity_search(query_embedding, limit=1)
        assert len(results) == 1
        print("✓ In-memory store similarity_search works")
        
        # Test 4: Similarity metrics
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        vec3 = np.array([1.0, 0.0, 0.0])
        
        sim_orthogonal = cosine_similarity(vec1, vec2)
        sim_identical = cosine_similarity(vec1, vec3)
        
        assert abs(sim_orthogonal - 0.0) < 1e-6  # Orthogonal vectors
        assert abs(sim_identical - 1.0) < 1e-6   # Identical vectors
        print("✓ Cosine similarity calculation works")
        
        # Test 5: Text processing
        preprocessor = TextPreprocessor()
        raw_text = "<p>This is   HTML   content!</p>"
        clean_text = preprocessor.preprocess(raw_text, clean_html=True, normalize_whitespace=True)
        assert "<p>" not in clean_text
        assert "  " not in clean_text  # No double spaces
        print("✓ Text preprocessing works")
        
        chunker = TextChunker()
        long_text = "This is a long text. " * 100
        chunks = chunker.chunk_text(long_text)
        assert len(chunks) > 1
        print("✓ Text chunking works")
        
        return True
        
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        logger.error(f"Basic functionality test error: {e}")
        return False


async def test_error_handling():
    """Test error handling and exceptions."""
    print("\nTesting error handling...")
    
    try:
        from vector_db.utils.exceptions import VectorDBError, EmbeddingError, VectorStoreError
        from vector_db.models.vector_models import VectorDocument
        import numpy as np
        
        # Test 1: Exception creation
        error = VectorDBError(
            message="Test error",
            error_code="TEST_ERROR",
            details={"test": "value"}
        )
        assert error.message == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert error.details["test"] == "value"
        print("✓ Exception creation works")
        
        # Test 2: Exception serialization
        error_dict = error.to_dict()
        assert error_dict["message"] == "Test error"
        assert error_dict["error_code"] == "TEST_ERROR"
        print("✓ Exception serialization works")
        
        # Test 3: Validation errors
        try:
            # This should raise an error due to empty content
            VectorDocument(
                content="",  # Empty content should fail
                embedding=np.array([1.0, 2.0, 3.0]),
                metadata=None
            )
            assert False, "Should have raised ValueError"
        except ValueError:
            print("✓ Input validation works")
        
        return True
        
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
        logger.error(f"Error handling test error: {e}")
        return False


async def test_integration_readiness():
    """Test readiness for integration with existing system."""
    print("\nTesting integration readiness...")
    
    try:
        # Check if existing modules can be imported
        try:
            from llm_service.repositories.models import BlogContent, ContentMetadata
            print("✓ Existing BlogContent model available")
            existing_system_available = True
        except ImportError:
            print("⚠ Existing system models not available (this is OK for standalone testing)")
            existing_system_available = False
        
        # Check if crawled content directory exists
        crawled_dir = Path("crawled_content")
        if crawled_dir.exists() and any(crawled_dir.iterdir()):
            print("✓ Crawled content directory found")
            has_content = True
        else:
            print("⚠ No crawled content found (run web crawler to test full integration)")
            has_content = False
        
        # Check if processed content directory exists
        processed_dir = Path("processed_content")
        if processed_dir.exists() and any(processed_dir.iterdir()):
            print("✓ Processed content directory found")
        else:
            print("⚠ No processed content found")
        
        return True
        
    except Exception as e:
        print(f"✗ Integration readiness test failed: {e}")
        logger.error(f"Integration readiness test error: {e}")
        return False


async def main():
    """Run all tests."""
    print("Vector Database Module Test Suite")
    print("=" * 50)
    
    test_results = []
    
    # Run tests
    test_results.append(await test_imports())
    test_results.append(await test_basic_functionality())
    test_results.append(await test_error_handling())
    test_results.append(await test_integration_readiness())
    
    # Summary
    print("\n" + "=" * 50)
    passed_tests = sum(test_results)
    total_tests = len(test_results)
    
    print(f"Test Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Vector database module is ready to use.")
        
        print("\nNext steps:")
        print("1. Install optional dependencies:")
        print("   pip install sentence-transformers  # For local embeddings")
        print("   pip install openai                 # For OpenAI embeddings")
        print("2. Set environment variables:")
        print("   export OPENAI_API_KEY='your-key'   # Optional")
        print("3. Run the example:")
        print("   python vector_db_example.py")
        print("4. Integrate with existing content:")
        print("   python vector_content_processor.py")
        
        return 0
    else:
        print("❌ Some tests failed. Check the error messages above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
