from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("BAAI/bge-small-en-v1.5")
query = "Represent this sentence for searching relevant passages: remote work"
doc = "REMOTE WORK POLICY -- v2.0\nEffective Date: 2024-03"

q_vec = model.encode(query, normalize_embeddings=True)
d_vec = model.encode([doc], normalize_embeddings=True)[0]

sim = np.dot(q_vec, d_vec)
print("True Cosine Similarity:", sim)
