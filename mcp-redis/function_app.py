import json
import logging
import os
import numpy as np
import redis
from openai import AzureOpenAI
from dotenv import load_dotenv

import azure.functions as func

load_dotenv()

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Configuración de Redis
r = redis.StrictRedis(
    host=os.getenv("REDIS_HOST"),
    port=os.getenv("REDIS_PORT"),
    password=os.getenv("REDIS_PWD"),
    ssl=True,
    db=os.getenv("REDIS_DB", 0),
    socket_timeout=3,
    socket_connect_timeout=3
)

# Configuración de Azure OpenAI
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-12-01-preview")
)

EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

# Constantes para las propiedades del tool
_QUERY_PROPERTY_NAME = "query"
_TOP_K_PROPERTY_NAME = "top_k"
_THRESHOLD_PROPERTY_NAME = "threshold"


class ToolProperty:
    def __init__(self, property_name: str, property_type: str, description: str):
        self.propertyName = property_name
        self.propertyType = property_type
        self.description = description

    def to_dict(self):
        return {
            "propertyName": self.propertyName,
            "propertyType": self.propertyType,
            "description": self.description,
        }


# Definir las propiedades del tool usando la clase ToolProperty
tool_properties_semantic_search = [
    ToolProperty(_QUERY_PROPERTY_NAME, "string", "El texto de consulta para buscar contenido similar."),
    ToolProperty(_TOP_K_PROPERTY_NAME, "number", "Número máximo de resultados a devolver (por defecto: 1)."),
    ToolProperty(_THRESHOLD_PROPERTY_NAME, "number", "Umbral mínimo de similitud (por defecto: 0.80)."),
]

# Convertir las propiedades del tool a JSON
tool_properties_semantic_search_json = json.dumps([prop.to_dict() for prop in tool_properties_semantic_search])


def embed_text(text: str) -> list[float]:
    """
    Genera embedding de un texto con Azure OpenAI.
    """
    logging.info("Generando embedding")
    try:
        resp = client.embeddings.create(
            model=EMBEDDING_DEPLOYMENT,
            input=text
        )
        return resp.data[0].embedding
    except Exception as e:
        logging.error(f"Error generando embedding: {e}")
        raise


def cosine_similarity(a, b) -> float:
    """
    Calcula similitud coseno entre dos vectores.
    """
    logging.info("Calculando similitud coseno")
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def fix_encoding(text: str) -> str:
    """
    Intenta corregir problemas de codificación de texto.
    """
    try:
        return text.encode("latin-1").decode("utf-8")
    except Exception:
        return text


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="semantic_search",
    description="Busca en Redis la respuesta más similar a la pregunta usando embeddings de Azure OpenAI.",
    toolProperties=tool_properties_semantic_search_json,
)
def semantic_search(context) -> str:
    """
    Busca en Redis la respuesta más similar a la pregunta usando embeddings de Azure OpenAI.
    Solo devuelve resultados si el score >= threshold.
    Si no hay coincidencias relevantes, devuelve None para que el agente consulte al LLM.

    Args:
        context: El contexto del trigger que contiene los argumentos de entrada.

    Returns:
        str: Resultado de la búsqueda semántica en formato JSON o mensaje de error.
    """
    try:
        # Parsear el contexto para obtener los argumentos
        content = json.loads(context)
        arguments = content.get("arguments", {})
        
        query = arguments.get(_QUERY_PROPERTY_NAME, "")
        top_k = arguments.get(_TOP_K_PROPERTY_NAME, 1)
        threshold = arguments.get(_THRESHOLD_PROPERTY_NAME, 0.80)

        if not query:
            return json.dumps({"error": "No se proporcionó una consulta"})

        logging.info(f"Query recibido: {query}")
        
        # Corregir codificación si es necesario
        query = fix_encoding(query)
        logging.info(f"Query corregido: {query}")

        # Probar conexión a Redis
        try:
            r.ping()
            logging.info("Conexión a Redis exitosa")
        except Exception as e:
            logging.error(f"Error de conexión a Redis: {e}")
            return json.dumps({"error": f"Error de conexión a Redis: {e}"})

        # Generar embedding de la consulta
        q_emb = embed_text(query)
        
        # Obtener todas las claves semánticas de Redis
        keys = r.keys("semantic:*")
        logging.info(f"Encontradas {len(keys)} claves en Redis")

        best_matches = []
        for key in keys:
            raw = r.get(key)
            if not raw:
                continue

            try:
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
            except json.JSONDecodeError as e:
                logging.warning(f"Error decodificando JSON para clave {key}: {e}")
                continue

        if not best_matches:
            # Devolver None para que el agente continúe con el LLM
            logging.info("No se encontraron coincidencias relevantes")
            return json.dumps({"result": None, "message": "No se encontraron coincidencias relevantes"})

        # Ordenar por score y devolver top_k
        best_matches.sort(key=lambda x: x["score"], reverse=True)
        top_results = best_matches[:top_k]
        main_response = top_results[0]["response"]  # texto plano
        
        logging.info(f"Mejor respuesta encontrada: {main_response} con score {top_results[0]['score']}")

        # Retornar en el formato esperado
        result = {
            "content": [
                {"type": "text", "text": main_response}
            ],
            "matches": top_results,
            "total_found": len(best_matches)
        }
        
        return json.dumps(result)

    except Exception as e:
        logging.error(f"Error en semantic_search: {e}")
        return json.dumps({"error": f"Error interno: {str(e)}"})
