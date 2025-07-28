# app/output_formatter.py
import os

def get_pdf_files(input_folder):
    """
    Returns a list of PDF filenames from the specified input folder.
    """
    pdf_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.pdf')]
    pdf_files.sort() # Ensure consistent order
    return pdf_files