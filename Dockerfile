FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the sentence-transformers model during the build
# 'all-MiniLM-L6-v2' is ~90MB, well within the 1GB limit.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy the rest of the application code
COPY . .

# Set environment variables for model path to ensure it's found at runtime
ENV SENTENCE_TRANSFORMERS_HOME=/root/.cache/torch/sentence_transformers

CMD ["python", "main.py"]