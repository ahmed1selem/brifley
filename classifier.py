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
        centroid_file = "classifier_centroids.pkl"
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
        
    raw_category = _categories[best_idx]
    
    # Clean up formatting for the UI (e.g., "WORLD NEWS" -> "World News")
    return raw_category.replace("_", " ").title()

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
