# https://fastapi.tiangolo.com/deployment/docker/
FROM python:3.11-alpine as requirements-stage

WORKDIR /tmp

# Instala poetry
RUN pip install poetry
# Copia solo el listado de dependencias
COPY ./pyproject.toml ./poetry.lock* /tmp/

# Compila el requirements.txt
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes


FROM python:3.11 as production-stage

WORKDIR /app

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instala las herramientas de PostgreSQL
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instala las dependencias
COPY --from=requirements-stage /tmp/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Copia los archivos de la aplicación
COPY . .

# Puerto expuesto
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
