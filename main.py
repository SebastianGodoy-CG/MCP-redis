from fastmcp import FastMCP
import redis
import os
import json
import numpy as np
from openai import AzureOpenAI

r = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=os.getenv("REDIS_PORT"),
    password=os.getenv("REDIS_PWD"),
    ssl=True,
    db=os.getenv("REDIS_DB", 0))

mcp = FastMCP("redis-mcp", version="1.0.0")

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-12-01-preview")
)

EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")


def embed_text(text: str) -> list[float]:
    """
    Genera embedding de un texto con Azure OpenAI.
    """
    resp = client.embeddings.create(
        model=EMBEDDING_DEPLOYMENT,  # nombre del deployment de embeddings en Azure
        input=text
    )
    return resp.data[0].embedding

def cosine_similarity(a, b) -> float:
    """
    Calcula similitud coseno entre dos vectores.
    """
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

@mcp.tool()
def semantic_search(query: str, top_k: int = 1) -> dict | None:
    """
    Busca en Redis la respuesta más similar a la pregunta usando embeddings de Azure OpenAI.
    """
    q_emb = embed_text(query)
    keys = r.keys("semantic:*")

    best_matches = []
    for key in keys:
        raw = r.get(key)
        if not raw:
            continue

        doc = json.loads(raw)
        if "embedding" not in doc or "response" not in doc:
            continue

        score = cosine_similarity(q_emb, doc["embedding"])
        best_matches.append({
            "key": key,
            "text": doc["text"],
            "response": doc["response"],
            "score": score
        })

    best_matches.sort(key=lambda x: x["score"], reverse=True)

    return best_matches[:top_k] if best_matches else None


if __name__ == "__main__":
    mcp.run()