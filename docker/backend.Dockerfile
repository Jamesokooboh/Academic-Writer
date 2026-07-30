FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
# CPU-only torch: the default PyPI wheel bundles CUDA and is ~4x larger for no benefit in a
# container with no GPU. Installed separately so it's satisfied before the rest of
# requirements.txt pulls in sentence-transformers (which depends on torch).
RUN pip install --no-cache-dir --timeout 120 --retries 5 torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --timeout 120 --retries 5 -r requirements.txt

COPY backend/ .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
