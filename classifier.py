import pickle
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from langdetect import detect

categories = {0: 'culture',
 1: 'finance',
 2: 'medical',
 3: 'politics',
 4: 'religion',
 5: 'sports',
 6: 'tech'}

arabicCategories = {
    'culture':'Culture',
   'finance': 'Finance',
    'medical':'Medical',
   'politics': 'Politics',
   'religion': 'Religion',
   'sports': 'Sports',
   'tech': 'Tech'
}
englishCategories = {
    'entertainment':'Culture',
   'business': 'Finance',
    '':'Medical',
   'politics': 'Politics',
   '': 'Religion',
   'sport': 'Sports',
   'tech': 'Tech'
}
def get_cat(paragrapgh):
    article=paragrapgh
    language = detect(article)
    if language=="ar" or language=="en" :
         count_vectorizer,tfidf_transformer,model=load_resources(language)
    else:
        return "lang not supported"
    articleCounts = count_vectorizer.transform([article])
    articleTFIDF = tfidf_transformer.transform(articleCounts)
    predicted = model.predict(articleTFIDF)
    if language=="ar":
        return arabicCategories[predicted[0]]
    elif language=="en":
        return englishCategories[predicted[0]]
    else:
        return "lang not supported"



def load_resources(language):
    with open(f'./classifier/{language}.pkl', "rb") as file:
        pipeline = pickle.load(file)
    count_vectorizer = pipeline.named_steps['vect']
    tfidf_transformer=pipeline.named_steps['tfidf']
    model = pipeline.named_steps['clf']
    return count_vectorizer,tfidf_transformer,model

if __name__ == '__main__':
    print('PyCharm')
