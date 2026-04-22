from sentence_transformers import SentenceTransformer, util

# Load pre-trained model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Sentences
sentences = [
    "I love machine learning",
    "AI is fascinating",
    "I enjoy playing football"
]

# Convert sentences to embeddings (vectors)
embeddings = model.encode(sentences)
print(embeddings)
# Compare similarity between sentences
similarity = util.cos_sim(embeddings[0], embeddings[1])

print("Similarity between sentence 1 and 2:", similarity.item())