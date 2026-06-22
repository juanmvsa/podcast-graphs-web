# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Pydantic migration for runtime validation
- Validated data loaders with error boundaries
- Error boundaries for graceful degradation
- Pydantic Settings for configuration management
- Quality metrics tracking
- Pipeline observability

---

## [0.3.0] - 2024-01-15

### Added
- Modular codebase structure with clean separation of concerns
- Comprehensive type hints throughout codebase
- Topic clustering with BERTopic
- Per-topic summary graphs
- Interactive topic browser in frontend
- Wikipedia-based entity disambiguation
- Caching for Wikipedia API calls

### Changed
- Refactored entity processing into modular subpackage
- Improved entity resolution with multi-stage pipeline
- Enhanced visualization with custom CSS themes
- Optimized batch processing with spaCy pipe

### Fixed
- Entity name normalization edge cases
- Place abbreviation handling
- Memory usage in large episode processing

### Documentation
- Added comprehensive README
- Created CLAUDE.md for project instructions
- Added inline documentation for all modules

---

## [0.2.0] - 2024-01-01

### Added
- Sentiment analysis for edge contexts
- Temporal position tracking (early/middle/late)
- Show-level aggregation and summary graphs
- CSV export for adjacency matrices
- Rich CLI output with progress bars

### Changed
- Migrated from pandas to polars for performance
- Improved stopword filtering
- Enhanced graph visualization with legends

### Fixed
- Unicode handling in entity names
- Edge weight calculation accuracy
- Visualization layout issues

---

## [0.1.0] - 2023-12-15

### Added
- Initial release
- Basic entity extraction with spaCy
- Graph construction with NetworkX
- Interactive visualization with pyvis
- JSON serialization of graphs
- Simple CLI interface
- Cloudflare Pages deployment

---

## Template for Future Entries

Copy this template when adding new entries:

```markdown
## [Version] - YYYY-MM-DD

### Added
- New features that were added

### Changed
- Changes to existing functionality

### Deprecated
- Features that will be removed in future versions

### Removed
- Features that were removed

### Fixed
- Bug fixes

### Security
- Security-related changes

### Documentation
- Documentation updates

### Performance
- Performance improvements

### Implementation Details
- Link to implementation docs: `docs/implementations/NNN_feature_name.md`
- Migration guide: [Link to migration guide]
- Breaking changes: [Yes/No]
```

---

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** version (X.0.0): Incompatible API changes
- **MINOR** version (0.X.0): New functionality, backward compatible
- **PATCH** version (0.0.X): Bug fixes, backward compatible

### Examples

- `0.3.0 → 0.3.1`: Bug fix (patch)
- `0.3.1 → 0.4.0`: New feature, no breaking changes (minor)
- `0.4.0 → 1.0.0`: Breaking API changes (major)

---

## Categories Explained

### Added
New features or capabilities that didn't exist before.

**Examples**:
- Added Pydantic validation for all data models
- Added error boundary decorators
- Added batch validation reporting

### Changed
Modifications to existing features or behavior.

**Examples**:
- Changed dict access to object attribute access
- Changed from TypedDict to BaseModel
- Improved error messages for validation failures

### Deprecated
Features marked for removal in future versions. Users should migrate away.

**Examples**:
- Deprecated direct dict-style data access (use object attributes)
- Deprecated unvalidated file loading (use validated loaders)

### Removed
Features that have been completely removed.

**Examples**:
- Removed TypedDict definitions (replaced with Pydantic models)
- Removed legacy configuration format

### Fixed
Bug fixes that correct incorrect behavior.

**Examples**:
- Fixed validation allowing end timestamp before start
- Fixed speaker pattern not matching "speaker_XX" format
- Fixed empty entity names passing validation

### Security
Changes related to security vulnerabilities or improvements.

**Examples**:
- Fixed path traversal vulnerability in file loading
- Added input sanitization for user-provided paths
- Updated dependencies with security patches

### Documentation
Updates to documentation, guides, or comments.

**Examples**:
- Added implementation guide for Pydantic migration
- Updated README with new features
- Added inline code examples

### Performance
Changes that improve performance or efficiency.

**Examples**:
- Optimized validation with model_validate_json
- Reduced memory usage with streaming validation
- Improved batch processing speed by 40%

---

## Breaking Changes

Mark breaking changes clearly with:

```markdown
### ⚠️ BREAKING CHANGES

- **Dict to Object Access**: Code using `segment['text']` must change to `segment.text`
- **Error Handling**: Must catch `ValidationError` instead of `KeyError`
- **Serialization**: Use `model.model_dump()` instead of `dict(model)`

**Migration Guide**: See `docs/implementations/001_pydantic_migration.md`
```

---

## Linking to Implementation Docs

For significant changes, link to detailed implementation documentation:

```markdown
### Added
- Pydantic validation for all data models
  - **Details**: `docs/implementations/001_pydantic_migration.md`
  - **Justification**: Catch data errors at boundaries
  - **Migration**: See Section 7 of implementation doc
```

---

## Example Complete Entry

```markdown
## [0.4.0] - 2024-02-01

### ⚠️ BREAKING CHANGES

- **Pydantic Migration**: All `TypedDict` replaced with Pydantic `BaseModel`
  - Dict access (`data['key']`) → Object access (`data.key`)
  - Must catch `ValidationError` at data boundaries
  - Serialization: `dict(obj)` → `obj.model_dump()`

**Migration Guide**: See `docs/implementations/001_pydantic_migration.md`

### Added
- Runtime validation with Pydantic models ([#001](docs/implementations/001_pydantic_migration.md))
  - `TranscriptSegment` validates timestamps, speaker pattern, non-empty text
  - `SentimentResult` validates score range [0.0, 1.0] and label literals
  - `EntityResult` filters empty entity names automatically
- Validated data loaders ([#002](docs/implementations/002_validated_data_loaders.md))
  - `load_and_validate()` for generic model validation
  - `load_transcript()` for transcript-specific loading
  - `load_batch()` for batch processing with reports
  - Detailed validation reports with file-level error tracking
- Error boundaries for graceful degradation ([#003](docs/implementations/003_error_boundaries.md))
  - `ProcessingResult[T]` type for explicit error handling
  - `@with_error_boundary` decorator for function wrapping
  - `@with_file_error_boundary` for file operations
  - Aggregate error reporting with failure breakdown

### Changed
- Migrated all `TypedDict` to Pydantic `BaseModel` in `types.py`
- Updated `pipeline.py` to use validated loaders
- Modified error handling throughout to use `ProcessingResult`
- Improved error messages with field-level validation details

### Fixed
- Invalid data now caught at load time instead of deep in pipeline
- Clear error messages showing exact field and constraint that failed
- Graceful handling of batch processing with partial failures

### Performance
- Initial validation adds ~50ms per file (acceptable for data integrity)
- Overall pipeline faster due to fewer crashes and retries
- Can optimize with `model_validate_json()` if needed

### Documentation
- Added `docs/IMPLEMENTATION_GUIDE.md` - Template for documenting changes
- Added `docs/implementations/001_pydantic_migration.md` - Pydantic migration details
- Added `docs/implementations/002_validated_data_loaders.md` - Data loader implementation
- Added `docs/implementations/003_error_boundaries.md` - Error handling patterns
- Updated CHANGELOG.md with new format

### Tests
- Added comprehensive validation tests in `tests/test_types_validation.py`
- Added data loader tests in `tests/test_loaders.py`
- Added error boundary tests in `tests/test_error_handling.py`
- Test coverage: 95%+ for new validation code

---

**Full Details**: See implementation documentation in `docs/implementations/`
**Migration Required**: Yes - See migration guides in implementation docs
**Backward Compatible**: No - Breaking changes to data access patterns
```

---

## Maintenance Guidelines

### When to Update

Update the changelog:
1. **Before merging PR** - Add unreleased entry
2. **On release** - Move unreleased to versioned section
3. **Immediately** - Don't let changes accumulate

### How to Update

1. **Find or create version section**:
   ```markdown
   ## [Unreleased]
   ```

2. **Add entry under appropriate category**:
   ```markdown
   ### Added
   - New feature description
   ```

3. **Link to implementation docs**:
   ```markdown
   - Feature name ([#001](docs/implementations/001_feature.md))
   ```

4. **Mark breaking changes**:
   ```markdown
   ### ⚠️ BREAKING CHANGES
   - Description and migration guide
   ```

### Review Checklist

Before releasing a version:
- [ ] All changes documented
- [ ] Breaking changes clearly marked
- [ ] Migration guides linked
- [ ] Version number follows semver
- [ ] Date is accurate
- [ ] Links work
- [ ] Implementation docs exist for major changes

---

## Questions?

For questions about changelog maintenance:
- See `docs/IMPLEMENTATION_GUIDE.md`
- Create issue with `documentation` label
- Refer to [Keep a Changelog](https://keepachangelog.com/)
