from fastmcp import FastMCP
import redis
import os
import json
import numpy as np
from openai import AzureOpenAI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

r = redis.StrictRedis(
    host=os.getenv("REDIS_HOST"),
    port=os.getenv("REDIS_PORT"),
    password=os.getenv("REDIS_PWD"),
    ssl=True,
    db=os.getenv("REDIS_DB", 0),
    socket_timeout=3,
    socket_connect_timeout=3)

    # Prueba de conexión a Redis
try:
    r.ping()
    print("Conexión a Redis exitosa")
except Exception as e:
    print(f"Error de conexión a Redis: {e}")

mcp = FastMCP("redis_mcp", version="1.0.0")


client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-12-01-preview")
)

app = mcp.http_app()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

def embed_text(text: str) -> list[float]:
    """
    Genera embedding de un texto con Azure OpenAI.
    """
    print("generando embedding")
    resp = client.embeddings.create(
        model=EMBEDDING_DEPLOYMENT,
        input=text
    )
    return resp.data[0].embedding

def cosine_similarity(a, b) -> float:
    """
    Calcula similitud coseno entre dos vectores.
    """
    print("calculando similitud coseno")
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

@mcp.tool()
def semantic_search(query: str, top_k: int = 1, threshold: float = 0.80) -> dict | None:
    """
    Busca en Redis la respuesta más similar a la pregunta usando embeddings de Azure OpenAI.
    Solo devuelve resultados si el score >= threshold.
    Si no hay coincidencias relevantes, devuelve None para que el agente consulte al LLM.
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
        if score >= threshold:  # solo guardamos si pasa el umbral
            best_matches.append({
                "key": key.decode("utf-8") if isinstance(key, bytes) else key,
                "text": doc.get("text", ""),
                "response": doc["response"],
                "score": score
            })

    if not best_matches:
        # Devolver None para que el agente continúe con el LLM
        return None

    # Ordenar por score y devolver top_k
    best_matches.sort(key=lambda x: x["score"], reverse=True)
    top_results = best_matches[:top_k]
    main_response = top_results[0]["response"]  # texto plano
    print(main_response)

    # Retornar en el formato esperado por Foundry
    return {
        "content": [
            {"type": "text", "text": main_response}#,  # texto plano
            #{"type": "json", "json": top_results}     # metadata completa
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=False)