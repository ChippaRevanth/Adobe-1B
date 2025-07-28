# app/summarizer.py (Final Summary Truncation and Cleaning)
from sentence_transformers import SentenceTransformer, util
import torch
import re

model_name = 'all-MiniLM-L6-v2'
try:
    summarizer_model = SentenceTransformer(model_name)
    print(f"Loaded SentenceTransformer model for summarization: {model_name}")
except Exception as e:
    print(f"Error loading SentenceTransformer model for summarization {model_name}: {e}. Please ensure it's pre-downloaded or available.")
    raise

# Reduced default num_sentences for conciseness
def summarize_text(text, num_sentences=4, query_embedding=None): # <--- num_sentences REDUCED
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    sentences = [s for s in sentences if len(s.split()) > 5] 
    if not sentences:
        return ""

    num_sentences = min(num_sentences, len(sentences))
    if num_sentences == 0:
        return ""

    sentence_embeddings = summarizer_model.encode(sentences, convert_to_tensor=True)

    if query_embedding is not None:
        similarities = util.pytorch_cos_sim(query_embedding, sentence_embeddings)[0]
        ranked_sentence_indices = torch.argsort(similarities, descending=True)
        
    else:
        cosine_scores = util.pytorch_cos_sim(sentence_embeddings, sentence_embeddings)
        sentence_scores = torch.sum(cosine_scores, dim=1)
        ranked_sentence_indices = torch.argsort(sentence_scores, descending=True)

    selected_sentences_content = []
    seen_sentences_content = set()
    
    for idx in ranked_sentence_indices:
        sentence = sentences[idx.item()]
        # Remove common bullet point chars from start of sentence for cleaner summary
        cleaned_sentence = re.sub(r"^\s*[\u2022\u2023\u25E6\u2043]+\s*", "", sentence).strip()
        
        if cleaned_sentence and cleaned_sentence not in seen_sentences_content:
            selected_sentences_content.append(cleaned_sentence)
            seen_sentences_content.add(cleaned_sentence)
        if len(selected_sentences_content) >= num_sentences:
            break
            
    final_ordered_sentences = []
    selected_cleaned_set = set(selected_sentences_content) 

    for s_original in sentences:
        s_original_cleaned = re.sub(r"^\s*[\u2022\u2023\u25E6\u2043]+\s*", "", s_original).strip()
        if s_original_cleaned in selected_cleaned_set:
            final_ordered_sentences.append(s_original)

    final_text = " ".join(final_ordered_sentences).strip()
    
    if final_text and not final_text.endswith(('.', '?', '!')):
        final_text += "."
    return final_text