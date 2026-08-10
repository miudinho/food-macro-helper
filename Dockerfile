FROM python:3.11-slim

RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY foods.json .

# Przekierowanie HOME do /tmp rozwiązuje problem braku uprawnień do zapisu metryk przez Streamlit
ENV HOME=/tmp

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]