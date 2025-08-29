import sys
import types
import pytest

import re
from pathlib import Path

import builtins

import importlib.util

# Dynamically import the script as a module
spec = importlib.util.spec_from_file_location(
    "add_page_numbers", str(Path(__file__).parent.parent / "add_page_numbers.py")
)
add_page_numbers = importlib.util.module_from_spec(spec)
sys.modules["add_page_numbers"] = add_page_numbers
spec.loader.exec_module(add_page_numbers)

def test_normalize():
    assert add_page_numbers.normalize("Hello   World!\n") == "hello world!"
    assert add_page_numbers.normalize("") == ""
    assert add_page_numbers.normalize("  A\tB\nC  ") == "a b c"

def test_get_snippets():
    text = "one two three four five six seven eight nine ten eleven twelve"
    s, e = add_page_numbers.get_snippets(text, n=3)
    assert s == "one two three"
    assert e == "ten eleven twelve"
    # If not enough words, returns full text for both
    s2, e2 = add_page_numbers.get_snippets("foo bar", n=5)
    assert s2 == "foo bar"
    assert e2 == "foo bar"

def test_find_best_match_basic():
    # Simple exact match
    src = [
        "this is a test page with some extra content at the end to make it longer than the minimum",
        "another page here with additional words for testing purposes to ensure it passes the minimum word count",
        "final page containing summary and conclusion and some more filler text to meet length requirements"
    ]
    snippet = "another page here with additional words for testing purposes to ensure it passes the minimum word count"
    
    # The snippet is now long enough to be processed
    assert add_page_numbers.find_best_match(snippet, src, direction='start', log_page=1) == 2
    # No match
    no_match_snippet = "this snippet is not present and is also long enough to be processed by the function"
    assert add_page_numbers.find_best_match(no_match_snippet, src, direction='start', log_page=1) == -1

def test_find_best_match_fuzzy():
    src = [
        "this is a test page with some extra content at the end to make it longer than the minimum", 
        "another page here with additional words for testing purposes to ensure it passes the minimum word count", 
        "final page containing summary and conclusion and some more filler text to meet length requirements"
    ]
    snippet = "another page here with additional words for testing purposes to ensure it passes the minimum word cunt"  # intentional typo
    # Lower threshold for this test
    orig = add_page_numbers.SNIPPET_CONFIDENCE_THRESHOLD
    add_page_numbers.SNIPPET_CONFIDENCE_THRESHOLD = 80
    try:
        # Use a snippet length that matches the test data
        assert add_page_numbers.find_best_match(snippet, src, direction='start', log_page=1) == 2
    finally:
        add_page_numbers.SNIPPET_CONFIDENCE_THRESHOLD = orig

def test_process_pdfs_smoke(monkeypatch, tmp_path):
    # Mock pymupdf and PDF objects
    class DummyPage:
        def __init__(self, text):
            self._text = text
            self.rect = types.SimpleNamespace(width=100, height=200)
            self.inserted = []
        def get_text(self, _):
            return self._text
        def insert_text(self, pos, label, **kwargs):
            self.inserted.append((pos, label, kwargs))
    class DummyDoc:
        def __init__(self, texts):
            self.pages = [DummyPage(t) for t in texts]
            self.page_count = len(self.pages)
        def __iter__(self):
            return iter(self.pages)
        def __getitem__(self, idx):
            return self.pages[idx]
        def close(self):
            pass
        def save(self, path, **kwargs):
            self.saved_path = path

    # Use identical text for source and target to guarantee a match
    # The text must be longer than MIN_SNIPPET_WORDS (10)
    page1_text = "this is the first page of the document and it is long enough for testing"
    page2_text = "this is the second page of the document and it is also long enough for testing"
    dummy_src = DummyDoc([page1_text, page2_text, "some other page"])
    dummy_tgt = DummyDoc([page1_text, page2_text])
    monkeypatch.setattr(add_page_numbers.pymupdf, "open", lambda path: dummy_src if "src" in str(path) else dummy_tgt)

    out_path = tmp_path / "out.pdf"
    add_page_numbers.process_pdfs("src.pdf", "tgt.pdf", out_path)
    # Check that save was called
    assert hasattr(dummy_tgt, "saved_path")
    assert dummy_tgt.saved_path == out_path
    # Check that insert_text was called on pages
    assert any(page.inserted for page in dummy_tgt.pages)

