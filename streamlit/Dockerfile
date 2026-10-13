FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
#COPY app.py .
# Copy the app, its modules and theme (not only app.py)
COPY . .

# Container = demo/deploy environment: read the live BigQuery mart only, never fall back silently
ENV MASAR_DATA_SOURCE=bigquery

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]

