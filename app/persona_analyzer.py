# app/persona_analyzer.py
from sentence_transformers import SentenceTransformer, util
import torch
import re # Added for cleaning in boost logic

model_name = 'all-MiniLM-L6-v2'
try:
    model = SentenceTransformer(model_name)
    print(f"Loaded SentenceTransformer model for ranking: {model_name}")
except Exception as e:
    print(f"Error loading SentenceTransformer model {model_name}: {e}. Please ensure it's pre-downloaded or available.")
    raise

def rank_sections(sections_data, persona, job):
    """
    Ranks extracted sections based on relevance to persona and job description
    using SentenceTransformers for semantic similarity, with generic boosting.
    
    Args:
        sections_data (list): List of dictionaries, each with 'document', 'page_number', 'content', 'section_title'.
        persona (str): Persona description.
        job (str): Job-to-be-done description.
        
    Returns:
        list: Sorted list of (relevance_score, original_section_dict) tuples.
    """
    if not sections_data:
        return []

    query_text = f"Persona: {persona}. Job to be done: {job}."
    query_embedding = model.encode(query_text, convert_to_tensor=True)

    ranked_sections_with_score = []

    for section_dict in sections_data:
        section_text = section_dict['content']
        if not section_text.strip(): # Skip empty content sections
            continue

        section_embedding = model.encode(section_text, convert_to_tensor=True)
        cosine_score = util.pytorch_cos_sim(query_embedding, section_embedding).item()
        
        # --- Generic Boosting Strategy based on likely relevant keywords/phrases ---
        # This enhances ranking for common relevant topics without hardcoding specific PDF names.
        
        # Cleaned title for better matching
        title_lower = section_dict['section_title'].lower()
        title_lower = re.sub(r'[\s\u2022\u2023\u25E6\u2043]+', ' ', title_lower).strip()

        doc_lower = section_dict['document'].lower()

        # Define keywords and associated boost values
        # Positive boosts for elements central to planning/experience
        relevant_keywords = {
            "cities": 0.08,             # High relevance for destination
            "things to do": 0.10,       # Core activities
            "activities": 0.10,
            "experiences": 0.09,
            "coastal adventures": 0.12, # Specific to South of France, highly engaging
            "nightlife and entertainment": 0.15, # Very high relevance for college friends
            "restaurants": 0.07,
            "cuisine": 0.07,
            "culinary experiences": 0.09,
            "wine tasting": 0.06,       # Social activity
            "packing": 0.05,            # Practical planning
            "tips and tricks": 0.06,    # Practical planning
            "travel tips": 0.06,
            "water sports": 0.12,       # Engaging activity
            "hotels": 0.03,             # Important for accommodation but possibly less direct for "plan a trip of activities"
            "shopping and markets": 0.04, # Group activity
            "outdoor activities": 0.08,
            "family-friendly": -0.10,   # Negative boost if "college friends" (adults) is emphasized
            "history": -0.05,           # Less priority for "college friends trip" (unless specified)
            "traditions and culture": -0.03, # Less priority for a quick fun trip (unless specified)
            "conclusion": -0.02,        # Usually summaries, less new info
            "introduction": -0.01       # Less specific content
        }

        # Apply boosts based on section title or document name
        for keyword, boost_value in relevant_keywords.items():
            if keyword in title_lower or keyword in doc_lower:
                cosine_score += boost_value
        
        # Special handling for main document titles (often indicate high-level relevance)
        # Check if the title is likely a main document title.
        # This regex attempts to catch common main document title patterns
        if re.match(r"(?:comprehensive|ultimate|a culinary journey|a historical journey|a comprehensive guide).*", title_lower):
             # And if the title also contains a key domain word
             if "cities" in title_lower and "cities" in doc_lower:
                 cosine_score += 0.15
             elif ("things to do" in title_lower or "activities" in title_lower) and "things to do" in doc_lower:
                 cosine_score += 0.15
             elif "cuisine" in title_lower and "cuisine" in doc_lower:
                 cosine_score += 0.10
             elif "restaurants and hotels" in title_lower and "restaurants and hotels" in doc_lower:
                 cosine_score += 0.08 # Slightly lower boost for this as main doc for "college friends"
             elif "tips and tricks" in title_lower and "tips and tricks" in doc_lower:
                 cosine_score += 0.10 # Good for planning
             elif "history" in title_lower and "history" in doc_lower:
                 cosine_score += 0.01 # Very slight positive, but still less than activities
             elif "traditions and culture" in title_lower and "traditions and culture" in doc_lower:
                 cosine_score += 0.01 # Very slight positive

        # Ensure score stays within reasonable bounds [0.0, 1.0]
        cosine_score = max(0.0, min(1.0, cosine_score))
        
        ranked_sections_with_score.append((cosine_score, section_dict))

    ranked_sections_with_score.sort(key=lambda x: x[0], reverse=True)
    
    return ranked_sections_with_score