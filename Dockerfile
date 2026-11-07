FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src
WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && useradd --uid 10001 --create-home ferremax \
    && chown ferremax:ferremax /app

COPY --chown=ferremax:ferremax src/ ./src/
COPY --chown=ferremax:ferremax scripts/cargar_inventario_demo.py scripts/cargar_cotizacion_demo.py ./scripts/
COPY --chown=ferremax:ferremax scripts/iniciar_api.py ./scripts/
# Mismo DDL que Compose y la suite; una sola definicion de las seis tablas.
COPY --chown=ferremax:ferremax tests/sql/ferremax_pruebas.sql ./tests/sql/

FROM base AS tests
COPY requirements-dev.txt ./
RUN python -m pip install --no-cache-dir -r requirements-dev.txt
COPY tests/ ./tests/
COPY examples/ ./examples/
COPY pytest.ini .coveragerc ./
COPY docker/run_tests.py ./docker/run_tests.py
# El servicio tests escribe reportes en un bind mount local, sin montar el codigo.
CMD ["python", "docker/run_tests.py"]

FROM base AS app
USER ferremax
EXPOSE 8000
CMD ["python", "scripts/iniciar_api.py"]
