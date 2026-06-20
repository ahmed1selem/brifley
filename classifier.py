"""
Kaggle Centroid Classifier

Loads the 42x512 Kaggle Centroid Matrix.
Embeds the incoming article and finds the closest Category Centroid using Cosine Similarity.
"""
import os
import pickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from clustering import get_embedder

_centroid_dict = None
_categories = None
_centroid_matrix = None

def get_cat(paragraph):
    global _centroid_dict, _categories, _centroid_matrix
    
    if not paragraph or len(paragraph.strip()) == 0:
        return "Unknown"
        
    # Lazy load the centroid matrix
    if _centroid_matrix is None:
        centroid_file = "./artifacts/classifier/classifier_centroids.pkl"
        if not os.path.exists(centroid_file):
            return "General News" # Fallback if file isn't built yet
            
        with open(centroid_file, "rb") as f:
            _centroid_dict = pickle.load(f)
            
        _categories = list(_centroid_dict.keys())
        _centroid_matrix = np.array([_centroid_dict[c] for c in _categories])
        
    embedder = get_embedder()
    art_embedding = embedder.encode([paragraph], show_progress_bar=False)
    
    similarities = cosine_similarity(art_embedding, _centroid_matrix)[0]
    
    best_idx = np.argmax(similarities)
    best_score = similarities[best_idx]
    
    # 0.15 threshold ensures we don't classify random gibberish
    if best_score < 0.15:
        return "General News"
        
    raw_category = _categories[best_idx].replace("_", " ").title()

    # Merge HuffPost-specific label variants into clean, consistent names.
    # "Worldpost" and "The Worldpost" are the same section — unifying them
    # is critical for category-aware clustering: articles about the same
    # story must land in the same bucket or they can never cluster together.
    _NORMALIZE = {
        "Worldpost":       "World News",
        "The Worldpost":   "World News",
        "World News":      "World News",
        "U.S. News":       "U.S. News",
        "Politics":        "Politics",
        "Tech":            "Technology",
        "Technology":      "Technology",
        "Science":         "Science",
        "Business":        "Business",
        "Money":           "Finance",
        "Finance":         "Finance",
        "Sports":          "Sports",
        "Crime":           "Crime",
        "Media":           "Media",
        "Entertainment":   "Entertainment",
        "Comedy":          "Entertainment",
        "Arts":            "Arts",
        "Culture":         "Arts",
        "Culture & Arts":  "Arts",
        "Environment":     "Environment",
        "Green":           "Environment",
        "Religion":        "Religion",
        "Education":       "Education",
        "College":         "Education",
        "Wellness":        "Health",
        "Travel":          "Travel",
        "Style & Beauty":  "Lifestyle",
        "Home & Living":   "Lifestyle",
        "Parenting":       "Lifestyle",
        "Parents":         "Lifestyle",
        "Taste":           "Lifestyle",
        "Food & Drink":    "Lifestyle",
        "Fifty":           "General News",
        "Impact":          "General News",
        "Good News":       "General News",
        "Weird News":      "General News",
        "Black Voices":    "General News",
        "Latino Voices":   "General News",
        "Women":           "General News",
    }

    return _NORMALIZE.get(raw_category, raw_category)

if __name__ == '__main__':
    # Simple test
    test_texts = [
        "Four days of extreme rain killed 7% of world's rarest orangutans, study says",
        "Deadly Sudan drone strike targets funeral procession",
        "Apple stock surges after unveiling new AI capabilities",
        "Real Madrid wins the Champions League final against Dortmund"
    ]
    for t in test_texts:
        print(f"'{t}' -> {get_cat(t)}")
