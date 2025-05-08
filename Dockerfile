# Use the official Python image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy project files into the container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port if needed (e.g., for a web application)
EXPOSE 5000

# Command to run the application (assuming the main file is app.py)
CMD ["python", "app.py"]
