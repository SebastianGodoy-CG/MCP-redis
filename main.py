from fastmcp import FastMCP
import redis
import os

r = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=os.getenv("REDIS_PORT"),
    password=os.getenv("REDIS_PWD"),
    ssl=True,
    db=os.getenv("REDIS_DB", 0))

mcp = FastMCP("redis-mcp", version="1.0.0")

#buscar valor por clave
@mcp.tool()
def redis_get(key: str) -> str | None:
    """
    Obtiene un valor de Redis por clave.
    """
    value = r.get(key)
    return value.decode("utf-8") if value else None


# Tool: guardar valor
@mcp.tool()
def redis_set(key: str, value: str, expire: int | None = None) -> str:
    """
    Guarda un valor en Redis. Expire es opcional (en segundos).
    """
    if expire:
        r.set(key, value, ex=expire)
    else:
        r.set(key, value)
    return "OK"


# Tool: eliminar valor
@mcp.tool()
def redis_del(key: str) -> str:
    """
    Elimina una clave de Redis.
    """
    r.delete(key)
    return "OK"


if __name__ == "__main__":
    mcp.run()