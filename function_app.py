import azure.functions as func
import logging
import redis
import os
import json
import numpy as np
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Redis client
r = redis.StrictRedis(
    host=os.getenv("REDIS_HOST"),
    port=os.getenv("REDIS_PORT"),
    password=os.getenv("REDIS_PWD"),
    ssl=True,
    db=int(os.getenv("REDIS_DB", 0)),
    socket_timeout=3,
    socket_connect_timeout=3
)

try:
    r.ping()
    logging.info("Conexión a Redis exitosa")
except Exception as e:
    logging.error(f"Error de conexión a Redis: {e}")

# Azure OpenAI client
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-12-01-preview")
)

EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

def embed_text(text: str) -> list[float]:
    logging.info("Generando embedding...")
    resp = client.embeddings.create(
        model=EMBEDDING_DEPLOYMENT,
        input=text
    )
    return resp.data[0].embedding

def cosine_similarity(a, b) -> float:
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def fix_encoding(text: str) -> str:
    try:
        return text.encode("latin-1").decode("utf-8")
    except Exception:
        return text

# --- La función HTTP ---
#@app.function_name(name="semantic_search")
@app.route(route="semantic_search", methods=["POST"])
def semantic_search(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid or missing JSON body"}),
            mimetype="application/json",
            status_code=400
        )

    query = data.get("query", "")
    threshold = float(data.get("threshold", 0.80))
    top_k = int(data.get("top_k", 1))

    if not query:
        return func.HttpResponse(
            json.dumps({"error": "Missing 'query' field"}),
            mimetype="application/json",
            status_code=400
        )

    logging.info(f"Query recibido: {query}")
    query = fix_encoding(query)
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
        if score >= threshold:
            best_matches.append({
                "key": key.decode("utf-8") if isinstance(key, bytes) else key,
                "text": doc.get("text", ""),
                "response": doc["response"],
                "score": score
            })

    if not best_matches:
        return func.HttpResponse(
            json.dumps({"content": []}),
            mimetype="application/json",
            status_code=200
        )

    best_matches.sort(key=lambda x: x["score"], reverse=True)
    top_results = best_matches[:top_k]
    main_response = top_results[0]["response"]

    logging.info(f"Mejor respuesta encontrada: {main_response}")

    return func.HttpResponse(
        json.dumps({
            "content": [{"type": "text", "text": main_response}]
        }),
        mimetype="application/json",
        status_code=200
    )
