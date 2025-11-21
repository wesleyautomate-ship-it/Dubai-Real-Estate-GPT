"""
OpenAI Embeddings Helper
Async interface for generating text embeddings
"""

import asyncio
import hashlib
from functools import lru_cache
from typing import List
from openai import AsyncOpenAI
from backend.config import OPENAI_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS

# Initialize async OpenAI client
client = AsyncOpenAI(api_key=OPENAI_API_KEY)


def normalize_text(text: str, max_length: int = 8000) -> str:
    """
    Normalize and truncate text for embedding
    
    Args:
        text: Input text
        max_length: Maximum character length
        
    Returns:
        Normalized text
    """
    # Remove excess whitespace
    text = " ".join(text.split())
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text


@lru_cache(maxsize=1000)
def _cache_key(text: str) -> str:
    """Generate cache key from text hash"""
    return hashlib.md5(text.encode()).hexdigest()


async def embed_text(
    text: str,
    model: str = EMBEDDING_MODEL,
    dimensions: int = EMBEDDING_DIMENSIONS,
    max_retries: int = 3
) -> List[float]:
    """
    Generate embedding for text using OpenAI
    
    Args:
        text: Text to embed
        model: OpenAI embedding model
        dimensions: Embedding dimensions
        max_retries: Maximum retry attempts
        
    Returns:
        List of embedding floats
        
    Raises:
        Exception: If embedding generation fails after retries
        
    Example:
        embedding = await embed_text("3 bedroom apartment in Dubai Marina")
    """
    # Normalize text
    text = normalize_text(text)
    
    # Retry loop with exponential backoff
    for attempt in range(max_retries):
        try:
            response = await client.embeddings.create(
                model=model,
                input=text,
                dimensions=dimensions if "text-embedding-3" in model else None
            )
            return response.data[0].embedding
        
        except Exception as e:
            if attempt == max_retries - 1:
                raise Exception(f"Embedding generation failed after {max_retries} attempts: {str(e)}")
            
            # Exponential backoff
            wait_time = 2 ** attempt
            await asyncio.sleep(wait_time)
    
    raise Exception("Embedding generation failed")


async def embed_batch(
    texts: List[str],
    model: str = EMBEDDING_MODEL,
    dimensions: int = EMBEDDING_DIMENSIONS,
    batch_size: int = 100
) -> List[List[float]]:
    """
    Generate embeddings for multiple texts (batched)
    
    Args:
        texts: List of texts to embed
        model: OpenAI embedding model
        dimensions: Embedding dimensions
        batch_size: Maximum texts per API call
        
    Returns:
        List of embeddings (same order as input texts)
        
    Example:
        embeddings = await embed_batch([
            "3 bedroom apartment",
            "luxury penthouse",
            "studio with view"
        ])
    """
    # Normalize all texts
    texts = [normalize_text(t) for t in texts]
    
    # Process in batches
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        try:
            response = await client.embeddings.create(
                model=model,
                input=batch,
                dimensions=dimensions if "text-embedding-3" in model else None
            )
            
            # Extract embeddings in order
            embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(embeddings)
        
        except Exception as e:
            # Fallback: process batch texts individually
            print(f"Batch embedding failed, falling back to individual: {str(e)}")
            for text in batch:
                try:
                    embedding = await embed_text(text, model, dimensions)
                    all_embeddings.append(embedding)
                except Exception as inner_e:
                    print(f"Failed to embed text: {text[:50]}... - {str(inner_e)}")
                    # Return zero vector as fallback
                    all_embeddings.append([0.0] * dimensions)
    
    return all_embeddings
