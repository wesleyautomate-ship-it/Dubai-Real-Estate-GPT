"""
Embeddings Helper
Async interface for generating text embeddings via Gemini (preferred) or OpenAI fallback.
"""

import asyncio
import hashlib
from functools import lru_cache
from typing import List

from backend.config import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    GEMINI_API_KEY,
    LLM_PROVIDER,
    OPENAI_API_KEY,
)

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover
    AsyncOpenAI = None

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover
    genai = None

# Initialize clients lazily
_openai_client = None
_gemini_ready = False


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


def _fit_dimensions(vec: List[float], target: int) -> List[float]:
    """Pad or truncate embedding to the target dimension."""
    if len(vec) == target:
        return vec
    if len(vec) > target:
        return vec[:target]
    return vec + [0.0] * (target - len(vec))


async def _embed_with_gemini(text: str, model: str, dimensions: int) -> List[float]:
    if not GEMINI_API_KEY or genai is None:
        raise RuntimeError("Gemini embedding requested but google-generativeai not available or GEMINI_API_KEY missing")
    global _gemini_ready
    if not _gemini_ready:
        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_ready = True
    # Gemini client is sync; run in thread to avoid blocking loop
    def _call():
        resp = genai.embed_content(model=model, content=text)
        vec = resp.get("embedding") or resp.get("values") or []
        return _fit_dimensions(list(vec), dimensions)
    return await asyncio.to_thread(_call)


async def _embed_with_openai(text: str, model: str, dimensions: int, max_retries: int = 3) -> List[float]:
    if not OPENAI_API_KEY or AsyncOpenAI is None:
        raise RuntimeError("OpenAI embedding requested but openai package or API key missing")
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    for attempt in range(max_retries):
        try:
            response = await _openai_client.embeddings.create(
                model=model,
                input=text,
                dimensions=dimensions if "text-embedding-3" in model else None
            )
            vec = response.data[0].embedding
            return _fit_dimensions(list(vec), dimensions)
        except Exception as e:
            if attempt == max_retries - 1:
                raise Exception(f"Embedding generation failed after {max_retries} attempts: {str(e)}")
            await asyncio.sleep(2 ** attempt)
    raise Exception("Embedding generation failed")


async def embed_text(
    text: str,
    model: str = EMBEDDING_MODEL,
    dimensions: int = EMBEDDING_DIMENSIONS,
    max_retries: int = 3
) -> List[float]:
    """
    Generate embedding for text using Gemini (preferred) or OpenAI fallback.
    
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
    provider = (LLM_PROVIDER or "gemini").lower()
    if provider == "gemini":
        gem_model = model
        if not gem_model.startswith("models/"):
            gem_model = "models/text-embedding-004"
        return await _embed_with_gemini(text, gem_model, dimensions)
    # fallback to openai if explicitly configured
    return await _embed_with_openai(text, model, dimensions, max_retries=max_retries)


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
    texts = [normalize_text(t) for t in texts]
    all_embeddings: List[List[float]] = []

    # Gemini API does not currently support large batch embedding; process individually
    if (LLM_PROVIDER or "gemini") == "gemini":
        for text in texts:
            try:
                emb = await _embed_with_gemini(text, model, dimensions)
            except Exception as e:
                print(f"Failed to embed text: {text[:50]}... - {str(e)}")
                emb = [0.0] * dimensions
            all_embeddings.append(emb)
        return all_embeddings

    # OpenAI batching
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            response = await _openai_client.embeddings.create(
                model=model,
                input=batch,
                dimensions=dimensions if "text-embedding-3" in model else None
            )
            embeddings = [_fit_dimensions(list(item.embedding), dimensions) for item in response.data]
            all_embeddings.extend(embeddings)
        except Exception as e:
            print(f"Batch embedding failed, falling back to individual: {str(e)}")
            for text in batch:
                try:
                    emb = await _embed_with_openai(text, model, dimensions)
                except Exception as inner_e:
                    print(f"Failed to embed text: {text[:50]}... - {str(inner_e)}")
                    emb = [0.0] * dimensions
                all_embeddings.append(emb)

    return all_embeddings
