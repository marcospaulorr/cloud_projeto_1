# Dockerfile
FROM python:3.10

# Diretório de trabalho
WORKDIR /app

# Copia os arquivos
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante da aplicação
COPY . .

# Executa o servidor Uvicorn
CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]
