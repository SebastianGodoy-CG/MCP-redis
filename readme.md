# MCP Functions Repository

Este repositorio contiene una colección de servidores MCP (Model Context Protocol) adaptados para ejecutarse como Azure Functions. Cada carpeta representa un servidor MCP independiente que puede ser desplegado como una Function App en Azure.

## Estructura del Repositorio

```
├── .github/workflows/          # Pipelines de CI/CD para cada MCP
├── mcp-redis/                  # Servidor MCP para búsqueda semántica en Redis
└── [futuras-carpetas-mcp]/     # Otros servidores MCP
```

## MCPs Disponibles

### 🔍 mcp-redis
**Propósito**: Servidor MCP para realizar búsqueda semántica en Redis usando embeddings de Azure OpenAI.

**Funcionalidades**:
- Búsqueda semántica con similitud coseno
- Integración con Azure OpenAI para embeddings
- Conexión a Redis con SSL
- Umbral de relevancia configurable

**Archivos principales**:
- [`function_app.py`](mcp-redis/function_app.py) - Implementación como Azure Function
- [`main.py`](mcp-redis/main.py) - Implementación MCP standalone con FastMCP
- [`host.json`](mcp-redis/host.json) - Configuración del runtime de Azure Functions

## Cómo Desplegar un MCP en Azure Functions

### Prerrequisitos
- Azure CLI instalado y configurado
- Python 3.12
- Azure Function Core Tools
- Una cuenta de Azure con permisos para crear recursos

### Pasos de Despliegue Manual

1. **Navegar a la carpeta del MCP**:
   ```bash
   cd mcp-redis  # o la carpeta del MCP que deseas desplegar
   ```

2. **Crear un entorno virtual**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Crear la Function App en Azure**:
   ```bash
   az functionapp create \
     --resource-group tu-resource-group \
     --consumption-plan-location eastus \
     --runtime python \
     --runtime-version 3.12 \
     --functions-version 4 \
     --name tu-function-app-name \
     --storage-account tu-storage-account
   ```

5. **Configurar variables de entorno**:
   ```bash
   az functionapp config appsettings set \
     --name tu-function-app-name \
     --resource-group tu-resource-group \
     --settings \
     REDIS_HOST=tu-redis-host \
     REDIS_PORT=6380 \
     REDIS_PWD=tu-redis-password \
     AZURE_OPENAI_ENDPOINT=tu-openai-endpoint \
     AZURE_OPENAI_API_KEY=tu-openai-api-key \
     AZURE_OPENAI_EMBEDDING_DEPLOYMENT=tu-embedding-model
   ```

6. **Desplegar la función**:
   ```bash
   func azure functionapp publish tu-function-app-name
   ```

### Despliegue Automático con GitHub Actions

Cada MCP incluye un workflow de GitHub Actions configurado en [`.github/workflows/`](.github/workflows/). Para usar el despliegue automático:

1. **Configurar secretos en GitHub**:
   - `AZUREAPPSERVICE_CLIENTID_*`
   - `AZUREAPPSERVICE_TENANTID_*`
   - `AZUREAPPSERVICE_SUBSCRIPTIONID_*`

2. **Hacer push a la rama correspondiente**:
   ```bash
   git push origin nombre-de-rama-del-mcp
   ```

3. El workflow se ejecutará automáticamente y desplegará la función.

## Configuración de Variables de Entorno

Cada MCP requiere diferentes variables de entorno. Consulta el archivo `.env.example` (si existe) en cada carpeta para ver las variables requeridas.

### Variables Comunes:
```bash
# Azure OpenAI (para MCPs que usan embeddings)
AZURE_OPENAI_ENDPOINT=https://tu-openai-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=tu-api-key
AZURE_OPENAI_API_VERSION=2023-12-01-preview
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002

# Específicas del MCP (ejemplo: Redis)
REDIS_HOST=tu-redis-host.redis.cache.windows.net
REDIS_PORT=6380
REDIS_PWD=tu-redis-password
REDIS_DB=0
```

## Estructura de Archivos por MCP

Cada carpeta MCP contiene:

- `function_app.py` - Punto de entrada para Azure Functions
- `main.py` - Implementación MCP standalone (opcional, para desarrollo/testing)
- `requirements.txt` - Dependencias de Python
- `host.json` - Configuración del runtime de Azure Functions
- `.funcignore` - Archivos a ignorar durante el despliegue
- `.env` - Variables de entorno locales (no incluir en git)

## Desarrollo Local

Para probar un MCP localmente:

1. **Usando Azure Functions Core Tools**:
   ```bash
   cd mcp-redis
   func start
   ```

2. **Usando la implementación standalone**:
   ```bash
   cd mcp-redis
   python main.py
   ```

## Contribuciones

Para agregar un nuevo MCP:

1. Crear una nueva carpeta con el nombre del MCP
2. Implementar tanto `function_app.py` como `main.py`
3. Añadir el workflow de GitHub Actions correspondiente
4. Actualizar este README con la información del nuevo MCP

## Soporte

Para problemas o preguntas sobre los MCPs:
- Revisar los logs en Azure Portal
- Verificar la configuración de variables de entorno
- Comprobar la conectividad con servicios externos (Redis, Azure OpenAI, etc.)

## Licencia

[Especificar licencia aquí]