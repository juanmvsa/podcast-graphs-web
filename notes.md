
## sunday - 12-april-2026


### part 1: the structure of types.py

the `types.py` file has **three categories** of types, each serving a different purpose:

#### 1. enums (lines 17-38) - controlled vocabularies

```python
class SentimentLabel(str, Enum):
  POSITIVE = "POSITIVE"
  NEGATIVE = "NEGATIVE"
  NEUTRAL = "NEUTRAL"
```

**purpose** : these are like 'multiple choice' options - only these exact values are allowed.


in my `types.py` file, the lines 17-38 are the following:

```python
class EntityType(str, Enum):
    """Entity classification produced by the NER stage."""

    PERSON = "PERSON"
    PLACE = "PLACE"
```

why `str`, `Enum` ?

- `Enum` makes it a controlled vocabulary. ([link](obsidian://open?vault=gnosis_v3&file=22_web_clippings%2Fenum_python_official_documentation_site_clipping) to my obsidian note with `Enum`'s official documentation.')
- `str` means it is json-serializable.


### `types.py`

