import os.path

import gensim
from gensim.models import KeyedVectors, Word2Vec
import numpy as np
import pandas as pd
from datasets import load_dataset
import re
import nltk
from fasttext_pybind import fasttext
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import fasttext
import gensim.downloader as api
import faiss
from nltk.corpus import wordnet
from nltk import pos_tag
from wefe.datasets import load_bingliu
from wefe.metrics import RNSB
from wefe.query import Query
from wefe.word_embedding_model import WordEmbeddingModel
import plotly.express as px


def get_wordnet_pos(word):#Generated by chatGPT
    """Map NLTK POS tag to a format WordNetLemmatizer understands."""
    tag = pos_tag([word])[0][1][0].upper()  # Get the first letter of POS tag
    tag_dict = {"J": wordnet.ADJ, "N": wordnet.NOUN, "V": wordnet.VERB, "R": wordnet.ADV}
    return tag_dict.get(tag, wordnet.NOUN)  # Default to NOUN if tag is unknown

def preprocess_text(inputString, lowercase, lemma, cleanPunctuation, stopword):
    newText = inputString
    if lowercase:
        #Do Lowercasing
        newText = newText.lower()

    #Tokenize the input
    tokenizedString = []
    for line in newText.splitlines():
        #Stores each line from input string as a tokenized array form of the original
        tokenizedString.append(line.split())
    newText = tokenizedString

    #Stopword Removal
    if stopword:
        #Load external stopword list
        mystops = stopwords.words('english')
        #From class colab, apply stopwords and tokenize
        mystops = set(mystops)
        newText = [[tok for tok in row if tok not in mystops] for row in newText]

    #Lemmatizer
    if lemma:
        #Lemmatize with NLTK
        lemmatizer = WordNetLemmatizer()
        newText = [[lemmatizer.lemmatize(word, get_wordnet_pos(word)) for word in row] for row in newText]

    if cleanPunctuation:
        #Generated by Chatgpt
        newText = [[re.sub(r'[^\w\s]', '', word) for word in row] for row in newText]

    #Row below generated by ChatGPT, removes empty string elements
    newText = [[element for element in row if element] for row in newText if row and any(row)]
    return newText

#If the data is not processed yet, process the data and store it.  Else, retrieve the processed data
processed_data_path = "processed_data_no_lemma.txt"
if not os.path.exists(processed_data_path):
    #Load the dataset
    print("Loading Dataset")
    from datasets import load_dataset
    nltk.download('averaged_perceptron_tagger_eng')

    dataset = load_dataset("wikipedia", "20220301.simple")
    text_feature = dataset["train"]["text"]

    # Preprocess the data
    preprocessed_feature = []
    for count, feature in enumerate(text_feature):
        if count % 1000 == 0:
            print(f"Preprocessing {count}")
        preprocessed_feature.extend(preprocess_text(feature, lowercase=True, lemma=False, cleanPunctuation=True, stopword=True))
    flat_feature = [" ".join(row) for row in preprocessed_feature if row]

    #Save data
    with open(processed_data_path, "w", encoding="utf-8") as f:
        for line in flat_feature:
            f.write(line + "\n")

def get_results(vectors):
    #pie - cake
    q1_vec1 = vectors.get_vector("pumpkin")
    q1_vec2 = vectors.get_vector("pie")
    q1_vec3 = vectors.get_vector("cake")
    result_vec = q1_vec1 - q1_vec2 + q1_vec3
    result_vec = result_vec / np.linalg.norm(result_vec)
    print(f"Query 1: pumpkin - pie + cake equals {vectors.similar_by_vector(result_vec, topn=5)} \n")

    #quilt, 10 closest words
    q2_results = vectors.most_similar("quilt", topn=10)
    print(f"Query 2: Top {len(q2_results)} nearest neighbors of \"quilt\"")
    for entry in q2_results:
        print(f"{entry[1]}: {entry[0]}")
    print()

    #apple + banana - grapefruit
    q3_vec1 = vectors.get_vector("apple")
    q3_vec2 = vectors.get_vector("banana")
    q3_vec3 = vectors.get_vector("grapefruit")
    result_vec3 = q3_vec1 + q3_vec2 - q3_vec3
    result_vec3 = result_vec3 / np.linalg.norm(result_vec) 
    print(f"Query 3: apple plus banana minus grapefruit equals {vectors.similar_by_vector(result_vec3, topn=5)} \n")

    #quilt, 10 closest words
    q4_results = vectors.most_similar("harrison", topn=10)
    print(f"Query 4: Top {len(q4_results)} nearest neighbors of \"harrison\"")
    for entry in q4_results:
        print(f"{entry[1]}: {entry[0]}")
    print()

    # #cosine similarity of howl and bark
    q5_vec1 = vectors.get_vector("howl")
    q5_vec2 = vectors.get_vector("bark")
    print(f"The cosine similarity result of howl and bark is: {np.dot(q5_vec1, q5_vec2)/(np.linalg.norm(q5_vec1)*np.linalg.norm(q5_vec2))}")

#Select the model to be used here
model_select = "pass" #Options: skip, cbow, wiki, google
if model_select == "pass": pass
elif model_select == "skip":
    skip_vector_name = "skip_gram_no_lemma.vec"
    print("Loading Skip-gram Model")
    if not os.path.isfile(skip_vector_name):
        print("Model file not found, training from scratch")
        # Load processed data from file correctly
        with open(processed_data_path, "r", encoding="utf-8") as f:
            corpus = [line.strip().split() for line in f if line.strip()]
        model = Word2Vec(sentences=corpus, vector_size=300, sg=1, min_count=1, workers=8)
        model.wv.save_word2vec_format(skip_vector_name)

    skip_gram_model = gensim.models.keyedvectors.load_word2vec_format(skip_vector_name)
    print("Skip-gram Model Loaded Successfully")
    print("Skip-gram results:")
    get_results(skip_gram_model)

elif model_select == "cbow":
    cbow_vector_name = "cbow_vector_no_lemma.vec"
    print("Loading CBOW Model")
    if not os.path.isfile(cbow_vector_name):
        print("Model file not found, training from scratch")
        # Load processed data from file correctly
        with open(processed_data_path, "r", encoding="utf-8") as f:
            corpus = [line.strip().split() for line in f if line.strip()]
        model = Word2Vec(sentences=corpus, vector_size=300, sg=0, min_count=1, workers=8)
        model.wv.save_word2vec_format(cbow_vector_name)

    cbow_model = gensim.models.keyedvectors.load_word2vec_format(cbow_vector_name)
    print("CBOW Model Loaded Successfully")
    print("CBOW results:")
    get_results(cbow_model)

elif model_select == "wiki":
    # Load fasttext wiki news embeddings
    print("Loading Wikipedia Model")
    wiki_model = gensim.models.keyedvectors.load_word2vec_format("wiki-news-300d-1M-subword.vec")
    print("Wikipedia Model Loaded Successfully")
    get_results(wiki_model)

elif model_select == "google":
    #Load word2vec model pretrained on 3m google news tokens(code from source site)
    print("Loading google news embeddings")
    wv = api.load('word2vec-google-news-300')
    print("Google News Embeddings Loaded Successfully!")
    get_results(wv)
else: print("model_select not chosen correctly!")

#2.4 starts here ---------------------------------------------------------------
#RNSB chosen
#link: https://wefe.readthedocs.io/en/latest/examples/replications.html

def evaluate(query: Query, model_name, short_model_name: str, model_args: dict = {}):
    # Fetch the model
    model = WordEmbeddingModel(model_name, short_model_name, **model_args)
    # Run the queries
    results = RNSB().run_query(query, model, lost_vocabulary_threshold=0.23, holdout=True, print_model_evaluation=True, n_iterations=100)
    # Show the results obtained with glove
    fig = px.bar(
        pd.DataFrame(
            results["negative_sentiment_distribution"].items(),
            columns=["Word", "Sentiment distribution"],
        ),
        x="Word",
        y="Sentiment distribution",
        title=f"{short_model_name} Negative Sentiment Distribution",
    )

    fig.update_yaxes(range=[0, 0.2])
    fig.show()

RNSB_words = [
    ["engineer"],
    ["developer"],
    ["designer"],
    ["programmer"],
    ["coder"],
]
bing_liu = load_bingliu()

# Create the query
query = Query(RNSB_words, [bing_liu["positive_words"], bing_liu["negative_words"]])

#Options: skip, cbow, wiki, google
bias_selector = "pass"

if bias_selector == "pass": pass
elif bias_selector == "skip":
    skip_gram_model = gensim.models.keyedvectors.load_word2vec_format("skip_gram_no_lemma.vec")
    evaluate(query, skip_gram_model, 'Skip-Gram Model')
elif bias_selector == "cbow":
    cbow_model = gensim.models.keyedvectors.load_word2vec_format("cbow.vec")
    evaluate(query, cbow_model, 'CBOW Model')
elif bias_selector == "wiki":
    wiki_model = gensim.models.keyedvectors.load_word2vec_format("wiki-news-300d-1M-subword.vec")
    evaluate(query, wiki_model, 'Wiki Embeddings Model')
elif bias_selector == "google":
    google_model = api.load('word2vec-google-news-300')
    evaluate(query, google_model, 'Google News Model')
else: print("bias_selector not chosen correctly!")

#-------------------------------------------------------------------------------------------------------
