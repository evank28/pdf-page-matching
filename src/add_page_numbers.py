# PDF Page Numbering Script (Version 2.3)
# ----------------------------------------
#
# Author: Gemini
# Date: August 27, 2025
#
# Description:
# This script synchronizes page numbers between two versions of the same book in PDF format.
# It takes a "source" PDF (e.g., a scanned copy with correct page numbers) and a "target"
# PDF (e.g., an EPUB conversion without page numbers and with different pagination).
#
# The script works by taking text snippets from the start and end of each page in the
# target PDF. It then searches the source PDF to find which pages contain these snippets.
# If a match isn't found, it automatically shortens the snippet and retries. The resulting
# page range is then adjusted by a user-provided offset and superimposed onto a new
# version of the target file.
#
#
# HOW TO USE THIS SCRIPT:
# -----------------------
#
# 1. INSTALL PYTHON:
#    If you don't have Python installed, download and install it from https://www.python.org/
#
# 2. INSTALL REQUIRED LIBRARIES:
#    You need to install two libraries: PyMuPDF for handling PDFs and thefuzz for text matching.
#    Note: The PyMuPDF library is imported under the name 'fitz'.
#    Open your terminal or command prompt and run the following commands:
#
#    pip install PyMuPDF
#    pip install thefuzz[python-Levenshtein]
#
# 3. PREPARE YOUR FILES:
#    Place this Python script (`add_page_numbers.py`) in the same folder as your two PDF files.
#
# 4. RUN THE SCRIPT:
#    Open your terminal or command prompt, navigate to the folder containing your files,
#    and run the script using the following command structure:
#
#    python add_page_numbers.py "source.pdf" "target.pdf" "output.pdf" [offset]
#
#    - [offset] is an optional integer to subtract from the found page numbers.
#
#    Example (no offset):
#    python add_page_numbers.py "scanned_book.pdf" "ebook_version.pdf" "final_book.pdf"
#
#    Example (with offset):
#    python add_page_numbers.py "scanned_book.pdf" "ebook_version.pdf" "final_book.pdf" 14
#
# 5. CHECK THE OUTPUT:
#    The script will print its progress and create the new PDF file in the same folder.
#

import pymupdf  # PyMuPDF is imported as 'fitz'
import sys
import re
from thefuzz import fuzz
# --- CONFIGURATION ---
# You can adjust these values to fine-tune the matching process.

# The number of words to use from the start and end of a page for searching.
SNIPPET_WORDS = 20

# The confidence score (out of 100) required for a text snippet to be considered a match.
SNIPPET_CONFIDENCE_THRESHOLD = 90

# --- Fallback Mechanism Configuration ---
# If a match fails, the script will retry with a shorter snippet.
MIN_SNIPPET_WORDS = 10
SNIPPET_REDUCTION_STEP = 5

# --- Static Offset ---
# A default offset value. This can be overridden by a command-line argument.
DEFAULT_PAGE_NUMBER_OFFSET = 0


# --- HELPER FUNCTIONS ---

def normalize_text(text):
    """
    Cleans and normalizes a block of text to make it easier to compare.
    """
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.lower().strip()

def get_text_snippets(text):
    """
    Creates search snippets from the start and end of a block of text.
    """
    if not text:
        return "", ""
    
    words = text.split()
    # Ensure there's enough text to create meaningful snippets
    if len(words) < SNIPPET_WORDS:
        return text, text

    start_snippet = " ".join(words[:SNIPPET_WORDS])
    end_snippet = " ".join(words[-SNIPPET_WORDS:])
    return start_snippet, end_snippet

def find_best_match_for_snippet(snippet, source_pages_text, start_search_index=0, direction='start', target_page_for_logging=0):
    """
    Searches for the best fuzzy match of a snippet within the source page texts.
    Includes a fallback mechanism to shorten the snippet and retry if no match is found.
    """
    if not snippet:
        return -1

    original_words = snippet.split()
    num_words = len(original_words)
    is_retrying = False

    while num_words >= MIN_SNIPPET_WORDS:
        if direction == 'start':
            current_snippet_words = original_words[:num_words]
        else:  # 'end'
            current_snippet_words = original_words[-num_words:]
        current_snippet = " ".join(current_snippet_words)

        if is_retrying:
            print(f"\r\033[K[i] Target Page {target_page_for_logging}: Retrying with shorter snippet ({num_words} words)...")

        best_match_page = -1
        highest_score = 0

        for i in range(start_search_index, len(source_pages_text)):
            source_text = source_pages_text[i]
            if not source_text:
                continue
            
            score = fuzz.partial_ratio(current_snippet, source_text)
            if score > highest_score:
                highest_score = score
                best_match_page = i + 1  # Page numbers are 1-indexed

        if highest_score >= SNIPPET_CONFIDENCE_THRESHOLD:
            return best_match_page

        is_retrying = True
        num_words -= SNIPPET_REDUCTION_STEP
    
    return -1


# --- MAIN SCRIPT LOGIC ---

def process_pdfs(source_path, target_path, output_path, offset=0):
    """
    Main function to perform the PDF processing and page numbering.
    """
    print(f"--- Starting PDF Page Numbering Process (v2.4) ---")
    if offset != 0:
        print(f"Using page number offset: -{offset}")

    try:
        source_doc = pymupdf.open(source_path)
        target_doc = pymupdf.open(target_path) # This document will be modified in memory
        print(f"Successfully loaded Source PDF: '{source_path}' ({source_doc.page_count} pages)")
        print(f"Successfully loaded Target PDF: '{target_path}' ({target_doc.page_count} pages)")
    except Exception as e:
        print(f"Error: Could not open PDF files. Please check the file paths.")
        print(f"Details: {e}")
        return

    print("\nStep 1: Analyzing source PDF and creating a searchable text map...")
    source_pages_text = [normalize_text(page.get_text("text")) for page in source_doc]
    print(f"Created text map for {len(source_pages_text)} pages from the source PDF.")

    print("\nStep 2: Processing target PDF and matching content to source pages...")
    total_pages = target_doc.page_count
    for i, page in enumerate(target_doc):
        progress = (i + 1) / total_pages
        bar_length = 40
        filled_length = int(bar_length * progress)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        print(f'\rProcessing Page {i+1}/{total_pages} [{bar}] {progress:.1%}', end='')

        target_text = page.get_text("text")
        normalized_target_text = normalize_text(target_text)
        
        if not normalized_target_text:
            continue

        start_snippet, end_snippet = get_text_snippets(normalized_target_text)
        current_target_page_num = i + 1

        start_page_num = find_best_match_for_snippet(start_snippet, source_pages_text, direction='start', target_page_for_logging=current_target_page_num)
        
        end_search_index = max(0, start_page_num - 1) if start_page_num != -1 else 0
        end_page_num = find_best_match_for_snippet(end_snippet, source_pages_text, end_search_index, direction='end', target_page_for_logging=current_target_page_num)

        page_number_text = ""
        
        # Apply offset and determine the page number string
        adj_start = start_page_num - offset if start_page_num != -1 else -1
        adj_end = end_page_num - offset if end_page_num != -1 else -1

        if adj_start > 0 and adj_end > 0:
            if adj_start == adj_end:
                page_number_text = f"Page: {adj_start}"
            else:
                page_number_text = f"Pages: {adj_start}–{adj_end}"
        elif adj_start > 0:
             page_number_text = f"Page: {adj_start} (?)"
        else:
            if start_page_num != -1: # Match was found, but offset made it non-positive
                 print(f"\r\033[K[!] Warning: Page number for target page {current_target_page_num} is non-positive after offset.")
            else: # No match was ever found
                 print(f"\r\033[K[!] Warning: Could not find a confident match for content on target page {current_target_page_num}.")

        if page_number_text:
            # We are now inserting text directly onto the page from the target_doc
            page_rect = page.rect
            text_position = pymupdf.Point(page_rect.width / 2, page_rect.height - 30)
            
            page.insert_text(
                text_position,
                page_number_text,
                fontsize=10,
                fontname="helv",
                color=(0.5, 0.5, 0.5),
            )

    try:
        print(f"\n\nStep 3: Saving the final numbered PDF to '{output_path}'...")
        # Save the modified target_doc to the new output path
        target_doc.save(output_path, garbage=4, deflate=True, clean=True)
        print("--- Process Complete! ---")
    except Exception as e:
        print(f"Error: Could not save the output file.")
        print(f"Details: {e}")

    source_doc.close()
    target_doc.close()


if __name__ == "__main__":
    if len(sys.argv) < 4 or len(sys.argv) > 5:
        print("Usage: python add_page_numbers.py <source_pdf> <target_pdf> <output_pdf> [offset]")
        print("Example: python add_page_numbers.py \"scanned.pdf\" \"epub.pdf\" \"output.pdf\" 14")
        sys.exit(1)

    source_file = sys.argv[1]
    target_file = sys.argv[2]
    output_file = sys.argv[3]
    offset = DEFAULT_PAGE_NUMBER_OFFSET

    if len(sys.argv) == 5:
        try:
            offset = int(sys.argv[4])
        except ValueError:
            print("Error: The [offset] argument must be an integer.")
            sys.exit(1)

    process_pdfs(source_file, target_file, output_file, offset)