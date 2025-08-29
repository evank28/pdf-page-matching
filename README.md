# PDF Page Matcher
A Python script to superimpose correct page numbers from a source PDF onto a target PDF that has different pagination.

## Getting Started

Run `uv sync` to install dependancies. 
Requires you have installed uv to the global python instance and that it is on the PATH.

## Usecase

Let's say you have a book in multiple formats. You have a PDF with page numbers. You have an EPUB that you've converted to a PDF, sizing it perfectly for your e-reader.

However, the PDF that originates from an EPUB does not have page numbers, and the default page numbers ("what page within the PDF is it") won't correspond to the page numbers from the original PDF. 

This is problematic - how can multiple readers refer to the same page numbers consistently?

The solution is to superimpose page numbers based on the original PDF.

This script accomplishes that. 

## Usage

### Example (no offset):

```python
python add_page_numbers.py "scanned_book.pdf" "ebook_version.pdf" "final_book.pdf"
```

### Example (with offset):

Useful if the original PDF had page numbers that vary from the "what page within the PDF is it" page numbering. Use offset to make the page number shown in a PDF viewer match the page number actually written on those pages, so that the superimposed page numbers match that as well.
```python
python add_page_numbers.py "scanned_book.pdf" "ebook_version.pdf" "final_book.pdf" 14
```
