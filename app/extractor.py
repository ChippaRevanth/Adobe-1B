# app/extractor.py (FINAL ATTEMPT: Prioritizing Correct Page Numbers for Content Blocks)
import PyPDF2
import re
import os

def clean_text_ligatures(text):
    """Clean common Unicode ligatures and replace multiple spaces/newlines with single space."""
    text = text.replace('\ufb04', 'ff').replace('\ufb03', 'fi').replace('\ufb01', 'fi')
    return re.sub(r'\s+', ' ', text).strip()

def is_potential_heading_balanced(line_raw):
    """
    Checks if a line looks like a potential heading (strong or sub).
    Less aggressive than previous 'hyper' versions to avoid over-splitting on noise.
    """
    line_clean = clean_text_ligatures(line_raw)
    
    if len(line_clean) < 5 or len(line_clean) > 100: # Adjust max length if titles are very long
        return False
    
    # Exclusions (common noise, page numbers, source tags, years)
    if re.search(r'\b(page|source)\s*\d+\b', line_clean, re.IGNORECASE) or \
       re.match(r'^\$', line_clean) or \
       re.search(r'\b\d{4}\b', line_clean):
        return False
        
    # Heuristic 1: All CAPS (strong indicator for main sections)
    if line_clean.isupper() and len(line_clean.split()) > 1:
        # Exclude common short ALL CAPS words that might not be true headings
        if line_clean.lower() in ["introduction", "conclusion", "references", "appendix"]:
            return False
        return True

    # Heuristic 2: Starts with Roman numerals, numbers, or single capital letter followed by period/space
    if re.match(r"^\s*([IVXLCDM]+\.|\d+(\.\d+)*\.|[A-Z]\.)\s+[A-Z]", line_clean):
        return True
        
    # Heuristic 3: Title Case and reasonable length, and not ending in sentence punctuation
    if line_clean.istitle() and len(line_clean.split()) < 15 and not re.search(r'[\.\?\!]$', line_clean):
        # Exclude common short title-cased words that might not be true headings
        if line_clean.lower() in ["chapter", "part", "section"]:
            return False
        return True

    # Heuristic 4: Starts with a common bullet point and then capitalized text
    if re.match(r"^\s*[\u2022\u2023\u25E6\u2043]\s+[A-Z]", line_clean) and len(line_clean.split()) > 1:
        return True

    return False


def extract_sections(pdf_path):
    sections = []
    full_text_pages_raw = [] # Stores raw content for each page

    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text = page.extract_text()
                full_text_pages_raw.append(text if text else "")

            if not full_text_pages_raw:
                return []

            # Add the entire document as a primary section (always starts on page 1)
            # This is critical for high-level relevance and serves as a fallback.
            main_document_title = "Untitled Document"
            if full_text_pages_raw[0]:
                first_page_lines = [line.strip() for line in full_text_pages_raw[0].split('\n') if line.strip()]
                if first_page_lines:
                    main_document_title = clean_text_ligatures(first_page_lines[0])

            sections.append({
                "document": pdf_path.split(os.sep)[-1],
                "page_number": 1,
                "section_title": clean_text_ligatures(main_document_title),
                "content": clean_text_ligatures("\n".join(full_text_pages_raw))
            })

            # Now, process page by page to identify more granular sections
            # Each time a potential heading is found, finalize the previous block
            # and start a new one, ensuring accurate page numbers.
            current_section_content_lines = []
            current_section_title = None
            current_section_start_page = 1 

            for page_idx, page_content_raw in enumerate(full_text_pages_raw):
                current_page_num = page_idx + 1 # Page numbers are 1-based
                lines = [line.strip() for line in page_content_raw.split('\n') if line.strip()]
                
                # If this is not the first page, and the previous section accumulated content,
                # consider if the first line of this new page is a heading.
                # This ensures multi-page sections are properly handled.
                if page_idx > 0 and lines and current_section_content_lines:
                    first_line_of_page = lines[0]
                    if is_potential_heading_balanced(first_line_of_page) and \
                       (current_section_title is None or \
                        (clean_text_ligatures(first_line_of_page).lower() != current_section_title.lower() and \
                         clean_text_ligatures(first_line_of_page).lower() not in current_section_title.lower() and \
                         current_section_title.lower() not in clean_text_ligatures(first_line_of_page).lower())):
                        
                        # Finalize the previous section that spanned pages
                        content_to_add = clean_text_ligatures("\n".join(current_section_content_lines))
                        if content_to_add and len(content_to_add.split()) > 20: # Ensure meaningful content
                            sections.append({
                                "document": pdf_path.split(os.sep)[-1],
                                "page_number": current_section_start_page,
                                "section_title": current_section_title,
                                "content": content_to_add
                            })
                            # Start a new section with this new page's heading
                            current_section_content_lines = [first_line_of_page]
                            current_section_title = clean_text_ligatures(first_line_of_page)
                            current_section_start_page = current_page_num
                            lines = lines[1:] # Process rest of lines on this page
                        # Else, if the content is not meaningful, just append the new line and continue.
                
                for i, line_raw in enumerate(lines):
                    # Check for internal headings within the current page
                    is_new_candidate_heading = is_potential_heading_balanced(line_raw)
                    
                    if is_new_candidate_heading:
                        # If a current section title exists and the new candidate is different and valid
                        if current_section_title is not None and \
                           clean_text_ligatures(line_raw).lower() != current_section_title.lower() and \
                           clean_text_ligatures(line_raw).lower() not in current_section_title.lower() and \
                           current_section_title.lower() not in clean_text_ligatures(line_raw).lower():
                            
                            # Finalize the previous content block
                            if current_section_content_lines:
                                content_to_add = clean_text_ligatures("\n".join(current_section_content_lines))
                                if content_to_add and len(content_to_add.split()) > 20:
                                    sections.append({
                                        "document": pdf_path.split(os.sep)[-1],
                                        "page_number": current_section_start_page, # Page where this finalized block started
                                        "section_title": current_section_title,
                                        "content": content_to_add
                                    })
                            
                            # Start a new section with this heading
                            current_section_content_lines = [line_raw]
                            current_section_title = clean_text_ligatures(line_raw)
                            current_section_start_page = current_page_num # This new section starts on current page
                        else: # First heading found in the entire loop OR too similar to current title
                            current_section_content_lines.append(line_raw) # Append to current content
                            if current_section_title is None: # If this is the very first content block
                                current_section_title = clean_text_ligatures(line_raw)
                                current_section_start_page = current_page_num # This content block starts on current page
                    else: # Not a heading, just content line
                        current_section_content_lines.append(line_raw)
            
            # Add the very last accumulated section block
            if current_section_content_lines and current_section_title:
                content_to_add = clean_text_ligatures("\n".join(current_section_content_lines))
                if content_to_add and len(content_to_add.split()) > 20:
                    sections.append({
                        "document": pdf_path.split(os.sep)[-1],
                        "page_number": current_section_start_page, # Page where this last block started
                        "section_title": current_section_title,
                        "content": content_to_add
                    })
        
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        
    # --- Final post-processing for cleaning and deduplication ---
    final_cleaned_sections = []
    seen_content_hashes = set() 
    
    for section in sections:
        section_content_clean = clean_text_ligatures(section['content'])
        section_title_clean = clean_text_ligatures(section['section_title'])
        
        # Heuristic to revert long, generic titles if they are essentially content
        if len(section_title_clean.split()) > 15 and len(section_content_clean.split()) > 50:
            section_title_clean = f"Content from Page {section['page_number']}"
            
        content_hash = hash(section_content_clean)
        
        if section_content_clean and content_hash not in seen_content_hashes:
            final_cleaned_sections.append({
                "document": section["document"],
                "page_number": section["page_number"],
                "section_title": section_title_clean,
                "content": section_content_clean
            })
            seen_content_hashes.add(content_hash)
            
    # Fallback: if somehow no sections were found (unlikely now), treat each page as a section
    if not final_cleaned_sections and full_text_pages_raw:
        for page_num, content_raw in enumerate(full_text_pages_raw):
            cleaned_content = clean_text_ligatures(content_raw)
            if cleaned_content:
                final_cleaned_sections.append({
                    "document": pdf_path.split(os.sep)[-1],
                    "page_number": page_num + 1,
                    "section_title": f"Content from Page {page_num + 1}",
                    "content": cleaned_content
                })

    return final_cleaned_sections