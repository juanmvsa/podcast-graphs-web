# Hugging Face Model URL Fixes

## Summary
Updated all Hugging Face model references to use the correct full organization paths for better reliability and to avoid potential 404 errors.

## Changes Made

### 1. Sentiment Analysis Model
**File**: `scripts/generate_entity_graphs.py`

**Before**:
```python
model="distilbert-base-uncased-finetuned-sst-2-english"
```

**After**:
```python
model="distilbert/distilbert-base-uncased-finetuned-sst-2-english"
```

**Model Details**:
- Full path: [distilbert/distilbert-base-uncased-finetuned-sst-2-english](https://huggingface.co/distilbert/distilbert-base-uncased-finetuned-sst-2-english)
- Size: ~250MB
- Task: Sentiment analysis (POSITIVE/NEGATIVE/NEUTRAL)
- Downloads: 3.5M+
- Verified: ✅ Model exists and is actively maintained

### 2. Topic Modeling Embeddings (BERTopic)
**File**: `scripts/generate_entity_graphs.py`

**Before**:
```python
topic_model = BERTopic(
    min_topic_size=min_topic_size,
    nr_topics=nr_topics,
    # ... (used default embedding model implicitly)
)
```

**After**:
```python
from sentence_transformers import SentenceTransformer
embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

topic_model = BERTopic(
    embedding_model=embedding_model,
    min_topic_size=min_topic_size,
    nr_topics=nr_topics,
    # ...
)
```

**Model Details**:
- Full path: [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- Size: ~80MB
- Task: Sentence embeddings for topic modeling
- Downloads: 199.5M+
- Verified: ✅ Model exists and is the most popular sentence transformer

### 3. Dependencies Updated
**File**: `pyproject.toml`

Added explicit dependency:
```toml
"sentence-transformers>=2.0.0",
```

This ensures the SentenceTransformer library is properly installed.

### 4. Documentation Updated
**File**: `README.md`

Updated all references to include:
- Full model paths with organization names
- Direct links to Hugging Face model cards
- Accurate model sizes
- Clear indication of which models auto-download vs require manual installation

## Benefits

1. **Explicit Model References**: Using full organization/model-name paths prevents ambiguity
2. **Better Error Messages**: If a model doesn't exist, errors will be clearer
3. **Documentation**: Links to model cards help users understand what's being used
4. **Future-Proof**: Less likely to break if Hugging Face changes defaults
5. **Transparency**: Users can verify models before downloading

## Verification

All models were verified using the Hugging Face Hub API:

```bash
✅ distilbert/distilbert-base-uncased-finetuned-sst-2-english
   - Downloads: 3.5M
   - Task: text-classification
   - License: apache-2.0

✅ sentence-transformers/all-MiniLM-L6-v2
   - Downloads: 199.5M
   - Task: sentence-similarity
   - License: apache-2.0
```

## Testing

To test the fixes, run:

```bash
# Install updated dependencies
uv sync

# Run graph generation (models will auto-download with correct paths)
uv run scripts/generate_entity_graphs.py
```

## Next Steps

If you encounter any model download issues:

1. Check internet connection
2. Verify Hugging Face is accessible: https://huggingface.co
3. Clear cache if needed: `rm -rf ~/.cache/huggingface/`
4. Check logs for specific error messages

---

**Updated**: March 8, 2026
**Files Modified**: 3 files (generate_entity_graphs.py, pyproject.toml, README.md)
