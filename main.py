# main.py
import json
import time
import os
import argparse
import re
from sentence_transformers import SentenceTransformer, util

from app.extractor import extract_sections
from app.persona_analyzer import rank_sections
from app.summarizer import summarize_text
from app.output_formatter import get_pdf_files

INPUT_FOLDER_REL = "data/input"
OUTPUT_FILE_REL = "output/result.json"
INPUT_CONFIG_FILE_REL = os.path.join(INPUT_FOLDER_REL, "input_config.json")

# Load the model once globally for efficiency.
# This model will be available because of Dockerfile's RUN command.
try:
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("Main: Loaded SentenceTransformer model for query embedding.")
except Exception as e:
    print(f"Main: Error loading SentenceTransformer model: {e}. Ensure it's pre-downloaded.")
    # This is a critical error, so re-raise as the system cannot function without it.
    raise

def process():
    start_time = time.time()
    
    # Define absolute paths based on the current working directory (which is /app inside Docker)
    input_folder_abs = os.path.join(os.getcwd(), INPUT_FOLDER_REL)
    output_file_abs = os.path.join(os.getcwd(), OUTPUT_FILE_REL)
    input_config_file_abs = os.path.join(os.getcwd(), INPUT_CONFIG_FILE_REL)

    # Ensure the output directory exists
    os.makedirs(os.path.dirname(output_file_abs), exist_ok=True)

    # Default persona and job descriptions for fallback if input_config.json is missing or malformed
    persona_desc = "General Analyst"
    job_desc = "Extract key information from documents."
    input_documents_list = []

    # --- Load persona and job from input_config.json ---
    if os.path.exists(input_config_file_abs):
        try:
            with open(input_config_file_abs, 'r') as f:
                config_data = json.load(f)
                persona_desc = config_data.get('persona', {}).get('description', persona_desc)
                job_desc = config_data.get('job_to_be_done', {}).get('task', job_desc)
                input_documents_list = [doc['filename'] for doc in config_data.get('documents', [])]
                print(f"Loaded persona and job from {input_config_file_abs}.")
        except Exception as e:
            print(f"Error loading {input_config_file_abs}: {e}. Using default persona/job.")
    else:
        print(f"No {input_config_file_abs} found. Using default persona/job and discovering PDFs.")
        
    # If the document list was not provided in the config, discover PDFs from the input folder
    if not input_documents_list:
        input_documents_list = get_pdf_files(input_folder_abs)

    print(f"Processing for Persona: {persona_desc} | Job: {job_desc}")

    all_extracted_sections_for_ranking = [] 
    
    # --- Step 1: Extract sections from all PDFs ---
    for file_name in input_documents_list:
        path = os.path.join(input_folder_abs, file_name)
        if not os.path.exists(path):
            print(f"Error: PDF file '{file_name}' not found at '{path}'. Skipping.")
            continue
        print(f"Extracting sections from {file_name}...")
        
        # `extract_sections` returns a list of dictionaries: {'document', 'page_number', 'section_title', 'content'}
        sections_for_file = extract_sections(path)
        all_extracted_sections_for_ranking.extend(sections_for_file)

    if not all_extracted_sections_for_ranking:
        print("No sections extracted from any documents. Exiting.")
        return

    # --- Step 2: Rank all extracted sections globally based on persona and job ---
    print(f"Ranking {len(all_extracted_sections_for_ranking)} sections globally...")
    # `rank_sections` returns a list of (relevance_score, original_section_dict) tuples, sorted by score.
    ranked_sections_with_scores = rank_sections(all_extracted_sections_for_ranking, persona_desc, job_desc)

    # --- Step 3: Populate 'extracted_sections' for output (top N globally ranked sections) ---
    # The challenge's sample output typically shows a fixed number of top sections (e.g., 5).
    num_top_sections_to_output = 5 
    final_extracted_sections_for_output = []
    
    # Iterate through the globally ranked sections and pick the top N
    for i, (score, section_dict) in enumerate(ranked_sections_with_scores[:num_top_sections_to_output]):
        final_extracted_sections_for_output.append({
            "document": section_dict['document'],
            "page_number": section_dict['page_number'],
            "section_title": section_dict['section_title'],
            "importance_rank": i + 1 # Assign a global rank (1 to N)
        })
    
    # --- Step 4: Generate 'sub_section_analysis' ('refined_text') for the selected top sections ---
    sub_section_analysis_results = []
    
    # Create the query embedding once for summarization based on persona and job
    query_for_summarization_embedding = embedding_model.encode(f"{persona_desc} {job_desc}", convert_to_tensor=True)

    # Iterate through the sections that *made it into the final_extracted_sections_for_output*
    # to generate their summaries.
    for section_data_in_output in final_extracted_sections_for_output: 
        full_content_for_summary = ""
        # Find the original full content for this section from the `all_extracted_sections_for_ranking` list.
        # This ensures we summarize the complete content of the identified section.
        for raw_section in all_extracted_sections_for_ranking:
            # Match by document, page number, and section title for robustness
            if raw_section['document'] == section_data_in_output['document'] and \
               raw_section['page_number'] == section_data_in_output['page_number'] and \
               raw_section['section_title'] == section_data_in_output['section_title']:
                full_content_for_summary = raw_section['content']
                break
        
        if full_content_for_summary.strip(): # Only summarize if content exists
            print(f"Summarizing section: {section_data_in_output['section_title']} from {section_data_in_output['document']} (Page {section_data_in_output['page_number']})...")
            # Use query-based summarization to make refined text persona-relevant
            # You can adjust `num_sentences` here for shorter/longer summaries
            refined_text = summarize_text(full_content_for_summary, num_sentences=7, query_embedding=query_for_summarization_embedding)
            
            sub_section_analysis_results.append({
                "document": section_data_in_output['document'],
                "refined_text": refined_text,
                "page_number": section_data_in_output['page_number']
            })
    
    # Sort sub_section_analysis results by document name then page number for consistent output
    sub_section_analysis_results.sort(key=lambda x: (x['document'], x['page_number']))

    # --- Final Output Construction ---
    output_data = {
        "metadata": {
            "input_documents": input_documents_list,
            "persona": persona_desc,
            "job_to_be_done": job_desc,
            "processing_timestamp": time.strftime("%Y-%m-%d %H:%M:%S") # Generate current timestamp
        },
        "extracted_sections": final_extracted_sections_for_output,
        "sub_section_analysis": sub_section_analysis_results
    }

    # Write the final JSON output to the specified file
    with open(output_file_abs, "w") as f:
        json.dump(output_data, f, indent=4)

    print(f"✅ Completed in {round(time.time() - start_time, 2)}s. Output saved to {output_file_abs}")

if __name__ == "__main__":
    # This entry point runs the processing logic.
    # It relies on Docker's volume mounts to provide PDFs in `data/input`
    # and to collect the output from `output/result.json`.
    process()