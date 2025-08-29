"""
Synchronize page numbers between two versions of a book in PDF format.

Explanation:
    This script synchronizes page numbers between two versions of the same book in PDF format.
    It takes a "source" PDF (e.g., a scanned copy with correct page numbers) and a "target"
    PDF (e.g., an EPUB conversion without page numbers and with different pagination).

    The script works by taking text snippets from the start and end of each page in the
    target PDF. It then searches the source PDF to find which pages contain these snippets.
    If a match isn't found, it automatically shortens the snippet and retries. The resulting
    page range is then adjusted by a user-provided offset and superimposed onto a new
    version of the target file.

Usage:
    python add_page_numbers.py source.pdf target.pdf output.pdf [offset]
"""

import sys
import re
from pathlib import Path

import pymupdf  # PyMuPDF is imported as 'pymupdf'
from thefuzz import fuzz

# --- CONFIGURATION ---
# The number of words to use from the start and end of a page for searching.
SNIPPET_WORDS = 20

# The confidence score (out of 100) required for a text snippet to be considered a match.
SNIPPET_CONFIDENCE_THRESHOLD = 90

# If a match fails, the script will retry with a shorter snippet.
MIN_SNIPPET_WORDS = 10
SNIPPET_REDUCTION_STEP = 5

# A default offset value. This can be overridden by a command-line argument.
DEFAULT_OFFSET = 0

def normalize(text):
    """Cleans and normalizes a block of text to make it easier to compare."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).lower().strip()

def get_snippets(text, n=SNIPPET_WORDS):
    """Creates search snippets from the start and end of a block of text."""
    words = text.split()
    if len(words) < n:
        return text, text
    return " ".join(words[:n]), " ".join(words[-n:])

def find_best_match(snippet, source_texts, start_idx=0, direction='start', log_page=0):
    """
    Searches for the best fuzzy match of a snippet within the source page texts.
    Includes a fallback mechanism to shorten the snippet and retry if no match is found.
    """
    if not snippet:
        return -1
    words = snippet.split()
    n = len(words)
    retry = False
    while n >= MIN_SNIPPET_WORDS:
        curr = " ".join(words[:n]) if direction == 'start' else " ".join(words[-n:])
        if retry:
            print(f"\r[i] Target Page {log_page}: Retrying with {n} words...", end='')
        best, score = -1, 0
        for i, src in enumerate(source_texts[start_idx:], start=start_idx):
            if not src:
                continue
            s = fuzz.partial_ratio(curr, src)
            if s > score:
                score, best = s, i + 1
        if score >= SNIPPET_CONFIDENCE_THRESHOLD:
            return best
        retry = True
        n -= SNIPPET_REDUCTION_STEP
    return -1

def process_pdfs(source_path, target_path, output_path, offset=0):
    """
    Main function to perform the PDF processing and page numbering.
    """
    print(f"--- PDF Page Numbering ---")
    if offset:
        print(f"Offset: -{offset}")
    try:
        src_doc = pymupdf.open(source_path)
        tgt_doc = pymupdf.open(target_path)
    except Exception as e:
        print(f"Error opening PDFs: {e}")
        return

    print("Analyzing source PDF...")
    src_texts = [normalize(p.get_text("text")) for p in src_doc]
    print(f"Source: {len(src_texts)} pages")

    print("Processing target PDF...")
    total = tgt_doc.page_count
    for i, page in enumerate(tgt_doc):
        progress = (i + 1) / total
        bar = '█' * int(40 * progress) + '-' * (40 - int(40 * progress))
        print(f'\rPage {i+1}/{total} [{bar}] {progress:.1%}', end='')

        tgt_text = normalize(page.get_text("text"))
        if not tgt_text:
            continue
        start_snip, end_snip = get_snippets(tgt_text)
        page_num = i + 1

        start_match = find_best_match(start_snip, src_texts, direction='start', log_page=page_num)
        end_idx = max(0, start_match - 1) if start_match != -1 else 0
        end_match = find_best_match(end_snip, src_texts, end_idx, direction='end', log_page=page_num)

        adj_start = start_match - offset if start_match != -1 else -1
        adj_end = end_match - offset if end_match != -1 else -1

        if adj_start > 0 and adj_end > 0:
            label = f"Page: {adj_start}" if adj_start == adj_end else f"Pages: {adj_start}–{adj_end}"
        elif adj_start > 0:
            label = f"Page: {adj_start} (?)"
        else:
            if start_match != -1:
                print(f"\r[!] Page {page_num}: non-positive after offset.")
            else:
                print(f"\r[!] No match for target page {page_num}.")
            label = ""

        if label:
            rect = page.rect
            pos = pymupdf.Point(rect.width / 2, rect.height - 30)
            page.insert_text(pos, label, fontsize=10, fontname="helv", color=(0.5, 0.5, 0.5))

    print(f"\nSaving to '{output_path}'...")
    try:
        tgt_doc.save(output_path, garbage=4, deflate=True, clean=True)
        print("Done.")
    except Exception as e:
        print(f"Error saving output: {e}")
    src_doc.close()
    tgt_doc.close()

def parse_args():
    if not (4 <= len(sys.argv) <= 5):
        print("Usage: python add_page_numbers.py <source_pdf> <target_pdf> <output_pdf> [offset]")
        sys.exit(1)
    src, tgt, out = map(Path, sys.argv[1:4])
    offset = int(sys.argv[4]) if len(sys.argv) == 5 else DEFAULT_OFFSET
    return src, tgt, out, offset

if __name__ == "__main__":
    src, tgt, out, offset = parse_args()
    process_pdfs(src, tgt, out, offset)