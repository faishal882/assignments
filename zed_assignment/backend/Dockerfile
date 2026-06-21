FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --disable-pip-version-check -r requirements.txt

COPY --chown=app:app backend/app ./app
COPY --chown=app:app backend/config.json ./config.json
COPY --chown=app:app backend/data ./data

USER app
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
