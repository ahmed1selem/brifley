"""
Clustering module for Briefley.

Embeds article summaries using SentenceTransformer and clusters related 
stories using AgglomerativeClustering on raw 512d embeddings.
"""
import re
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
import nltk
import functools
import os

nltk.download('stopwords', quiet=True)
stopwordsEn = nltk.corpus.stopwords.words('english')
stopwordsAr = nltk.corpus.stopwords.words('arabic')

@functools.lru_cache(maxsize=1)
def get_embedder():
    """Lazy-load and cache the SentenceTransformer embedder."""
    return SentenceTransformer('./embadder/distiluse-base-multilingual-cased-v1')


def _is_arabic(text):
    """Fast Arabic detection using Unicode character range."""
    return bool(re.search(r'[\u0600-\u06FF]', text))


def remove_stopwords(text):
    """Remove stopwords from text based on detected language."""
    words = text.split()
    if _is_arabic(text):
        filtered_words = [word for word in words if word.lower() not in stopwordsAr]
    else:
        filtered_words = [word for word in words if word.lower() not in stopwordsEn]
    return ' '.join(filtered_words)


def clusters(data, min_cluster_size=2):
    """Cluster article summaries by semantic similarity.

    Args:
        data: List of dicts, each with at least 'id' and 'Summarized' keys.
        min_cluster_size: Minimum number of articles to form a cluster.

    Returns:
        dict mapping article IDs to cluster label strings.
        Articles labeled "-1" (noise) are filtered out.
    """
    # ---------------------------------------------------------------------------
    # DISTANCE THRESHOLD EXPLANATION:
    # Agglomerative clustering uses a distance threshold to form clusters.
    # We are using 'cosine' affinity, so the distance is (1 - cosine_similarity).
    # A threshold of 0.2 means articles must have a cosine similarity of >= 0.8 
    # to be clustered together.
    # ---------------------------------------------------------------------------
    distance_threshold = float(os.getenv("CLUSTER_DISTANCE_THRESHOLD", 0.65))
    df = pd.DataFrame(data)
    df = df.dropna(subset=["Summarized"])

    if len(df) < 2:
        return {}

    embedder = get_embedder()
    df['filtered_summary'] = df['Summarized'].apply(remove_stopwords)
    corpus_embeddings = embedder.encode(df['filtered_summary'])

    try:
        clusterer = AgglomerativeClustering(
            n_clusters=None,
            metric='cosine',
            linkage='average',
            distance_threshold=distance_threshold
        )
        labels = clusterer.fit_predict(corpus_embeddings)
    except TypeError:
        clusterer = AgglomerativeClustering(
            n_clusters=None,
            affinity='cosine',
            linkage='average',
            distance_threshold=distance_threshold
        )
        labels = clusterer.fit_predict(corpus_embeddings)

    df["label"] = labels
    
    # Filter out clusters smaller than min_cluster_size (convert to noise -1)
    label_counts = df["label"].value_counts()
    valid_labels = label_counts[label_counts >= min_cluster_size].index
    
    df["final_label"] = df["label"].apply(lambda x: str(x) if x in valid_labels else "-1")

    df_filtered = df[df["final_label"] != "-1"]
    return df_filtered.set_index("id")["final_label"].to_dict()

if __name__ == '__main__':
    print("Testing Clustering module...")
