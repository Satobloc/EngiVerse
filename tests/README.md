# Search prototype checks

The first search prototype is tested with Python's standard `unittest` runner:

```bash
python -m unittest discover -s tests -v
```

Tests use temporary local text files, never project evidence. They cover indexing, phrase search, Boolean search, source-hash reporting, integrity verification, and non-modification of original source files.
