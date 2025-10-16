# Use the lightweight Alpine base image
FROM python:3.11.13-alpine

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies and Python packages
RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev python3-dev py3-pip

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the crawler code into the container
COPY . .

# Define the command to run the crawler
CMD ["python", "main.py"]
