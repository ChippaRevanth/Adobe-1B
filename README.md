# Adobe-1B
"This project is a Python-based PDF document analysis tool. It extracts text, identifies key sections using PyPDF2 and sentence-transformers, then ranks and summarizes content based on a defined persona and task. Packaged with Docker for easy deployment, it provides persona-centric insights from PDFs without external network access."

This project processes PDF documents to extract, rank, and summarize content tailored to a specific user "persona" and "job-to-be-done". It intelligently identifies relevant sections and generates concise summaries, making large documents digestible for targeted insights.

1. Approach
Our solution employs a multi-stage pipeline for document analysis:

i)PDF Text Extraction: We utilize PyPDF2 to read PDF files and extract raw textual content page by page. A heuristic-based approach in extractor.py then identifies potential section titles and segments the document into meaningful content blocks, ensuring accurate page number association.

ii)Semantic Ranking: Each extracted section is semantically analyzed and ranked for relevance against a combined "persona" and "job-to-be-done" query. This is achieved using the SentenceTransformer model, which converts text into dense vector embeddings, allowing for cosine similarity comparisons to determine relevance. A boosting strategy is applied to enhance scores for sections containing keywords pertinent to common analysis tasks (e.g., cities, activities, culinary experiences for a travel planner persona).

iii)Query-Focused Summarization: The top-ranked sections are then summarized. We again use the SentenceTransformer model to generate sentence embeddings. Sentences within these sections are ranked based on their similarity to the original "persona" and "job-to-be-done" query, ensuring the generated summaries (refined_text) are concise and highly relevant to the user's immediate need.

iv)Output Generation: Finally, the processed data, including metadata, top extracted sections with their importance ranks, and the refined summaries, is compiled into a structured JSON output.

This modular design allows for independent development and potential future enhancements to each component.

2. Any Models or Libraries Used
The primary models and libraries utilized in this project are:

i)PyPDF2: For robust extraction of text content from PDF documents.

ii)sentence-transformers (Model: all-MiniLM-L6-v2): A powerful library for generating high-quality sentence embeddings. The all-MiniLM-L6-v2 model is used for both semantic ranking of document sections and for query-focused extractive summarization, ensuring content relevance. This model is pre-downloaded within the Docker image to ensure no internet access is required at runtime.
iii)torch: The underlying deep learning framework used by sentence-transformers for tensor operations.

iv)huggingface_hub: A dependency for sentence-transformers for model management.

v)Standard Python Libraries: json, os, time, argparse, re are used for file operations, argument parsing, timestamping, and regular expression-based text processing and cleaning.

3. How to Build and Run Your Solution (Documentation Purpose Only)
This section outlines the steps to build and run the Docker image containing the solution. Please note that the actual execution for evaluation will be handled via the "Expected Execution" section as mentioned in the submission checklist.

i)Prerequisites:
  Ensure you have Docker installed on your system.

ii)Clone the Repository:
  First, clone this Git repository to your local machine:
  git clone <https://github.com/ChippaRevanth/Adobe-1B.git>
  cd <Adobe-1B>
  
iii)Build the Docker Image:
  From the root directory of the cloned repository (where the Dockerfile resides), build the Docker image. This process will    install all dependencies and download the sentence-transformers model.
   ->docker build -t pdf-analyzer .
iv)Prepare Input (Optional for Testing):
  Place your input PDF files in a directory on your host machine. For example, create a folder named my_input_pdfs and put      your .pdf files inside it. You'll also need an input_config.json file in this input directory if you want to specify exact    documents, persona, and job-to-be-done, otherwise, the system will discover all PDFs and use defaults.
v)Run the Docker Container:
  To run the solution and process your PDFs, you will need to mount your input directory and an output directory as volumes.    The container expects input PDFs in /app/data/input and will write results to /app/output.
  docker run --rm \
    -v /path/to/your/input_folder:/app/data/input \
    -v /path/to/your/output_folder:/app/output \
    pdf-analyzer

 
 -Replace /path/to/your/output_folder with the absolute path to a local directory where you want the result.json output file    to be saved.

 -The pdf-analyzer at the end is the image tag you used during the build step.

 -The --rm flag automatically removes the container after it exits.

After execution, the result.json file will be available in your specified output folder on your host machine.



