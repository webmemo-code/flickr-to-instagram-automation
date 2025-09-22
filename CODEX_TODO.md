# CODEX TODO

## Status Snapshot
- EXIF-based hint extraction is in place (`flickr_api.py` now populates `photo_data['exif_hints']`; `blog_content_extractor.py` weights meta phrases and URLs accordingly).
- `caption_generator.py` prioritises EXIF-provided URLs, but recent edits left indentation issues (`account_code = ...` sits outside the `try` block, and the same variable is double-inserted). File needs cleanup.
- `test_blog_content_extractor.py` is updated and passing.
- `test_caption_generator.py` still reflects the pre-EXIF behaviour (fixtures lack `blog_post_urls`/`account`, mocks expect string context). Suite currently fails early during import because of the syntax error noted above.

## Immediate Tasks
1. **Fix `caption_generator.py` syntax**
   - Ensure `account_code = getattr(...)` is declared once inside `generate_caption` (after `context_text` assignment) and once at the top of `build_full_caption`.
   - Re-run `pytest test_suite/test_caption_generator.py -k "not live"` to confirm the SyntaxError is gone.

2. **Update caption tests to match new behaviour**
   - In the `config` fixture, set `config.blog_post_urls = [config.blog_post_url]` and `config.account = 'primary'`.
   - Update `sample_mauritius_photo_data` (and other stubs) to include `exif_hints` so code paths exercise the new logic.
   - Adjust tests that expect strings to work with `BlogContextMatch` (e.g., capture `.context` instead of the object, or patch `_get_blog_content_context` accordingly).
   - Add/restore a unit test covering EXIF prioritisation (mock `_load_blog_content`/`find_relevant_content` to assert EXIF URL wins).

3. **Stabilise mocks**
   - Wherever `CaptionGenerator` is instantiated in tests, patch `_get_blog_content_context` or `_load_blog_content` to avoid real HTTP calls and to satisfy new `blog_post_urls` usage.

4. **Regression pass**
   - Once tests compile, run:
     - `pytest test_suite/test_caption_generator.py -k "not live"`
     - `pytest test_suite/test_blog_content_extractor.py`
   - Optionally run any higher-level suites you normally exercise.

Now that the state’s captured in CODEX_TODO.md, finishing should be a straight sprint: clean the indentation, rewrite the tests with the new fixtures, and run the two pytest commands.

## Notes
- Ignore `.gitignore` change (present prior to this session); don’t revert.
- Temporary `_tmp_*.py` helper scripts have been removed; no cleanup required there.
- No commits made yet.
