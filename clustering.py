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
    return SentenceTransformer('./artifacts/embadder/distiluse-base-multilingual-cased-v1')


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


def embed(text: str) -> list:
    """Encode a single text string with stopword removal applied first.

    Use this for every embedding call — Qdrant storage, similarity queries,
    ground-truth verification — so stored vectors and query vectors are always
    produced the same way and cosine scores are meaningful.

    For batch encoding inside clusters() use remove_stopwords per-row then
    get_embedder().encode(batch) directly, to keep the batch efficient.
    """
    return get_embedder().encode(
        remove_stopwords(text), show_progress_bar=False
    ).tolist()


def _run_agglomerative(embeddings, distance_threshold):
    """Run AgglomerativeClustering, handling the metric/affinity API rename across sklearn versions."""
    kwargs = dict(n_clusters=None, linkage='average', distance_threshold=distance_threshold)
    try:
        return AgglomerativeClustering(metric='cosine', **kwargs).fit_predict(embeddings)
    except TypeError:
        return AgglomerativeClustering(affinity='cosine', **kwargs).fit_predict(embeddings)


def clusters(data, min_cluster_size=2):
    """Cluster article summaries by semantic similarity, within each category.

    Articles in different categories are never merged into the same cluster,
    preventing false positives caused by shared location/keyword signals
    (e.g. a World Cup story and an unrelated incident both tagged 'France').

    Distance threshold is (1 - cosine_similarity).  Default 0.30 means
    articles need cosine_similarity >= 0.70 to be grouped together.

    Args:
        data: List of dicts, each with at least 'id', 'Summarized', 'category'.
        min_cluster_size: Minimum articles required to form a valid cluster.

    Returns:
        dict mapping article IDs to globally unique cluster label strings.
        Articles that don't form a valid cluster are labeled "-1".
    """
    distance_threshold = float(os.getenv("CLUSTER_DISTANCE_THRESHOLD", 0.30))

    df = pd.DataFrame(data)
    df = df.dropna(subset=["Summarized"])

    if 'category' not in df.columns:
        df['category'] = 'General News'
    else:
        df['category'] = df['category'].fillna('General News')

    if len(df) < 2:
        return {}

    embedder = get_embedder()
    df['filtered_summary'] = df['Summarized'].apply(remove_stopwords)

    result = {}
    cluster_id_offset = 0

    for category, group in df.groupby('category'):
        ids = group['id'].tolist()

        if len(group) < 2:
            for aid in ids:
                result[aid] = "-1"
            continue

        embeddings = embedder.encode(group['filtered_summary'].tolist())
        labels = _run_agglomerative(embeddings, distance_threshold)

        label_counts = pd.Series(labels).value_counts()
        valid_labels = set(label_counts[label_counts >= min_cluster_size].index)

        for aid, label in zip(ids, labels):
            if label in valid_labels:
                result[aid] = str(label + cluster_id_offset)
            else:
                result[aid] = "-1"

        # Advance offset so IDs stay globally unique across categories
        if len(labels) > 0:
            cluster_id_offset += int(max(labels)) + 1

    return result

if __name__ == '__main__':
    print("Testing Clustering module...")
