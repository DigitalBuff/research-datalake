FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the data population script
COPY populate.py .

# Run the script
CMD ["python", "populate.py"]
