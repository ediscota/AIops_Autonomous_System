#!/bin/bash

# Starts the ollama server in the background
ollama serve &

# Wait the server is ready
sleep 5

# Downloads the specified model in the .env file
echo "Downloading model: $MODEL_NAME..."
ollama pull $MODEL_NAME

echo "Model ready!"

# Wait for the background process (the server) to not close the container
wait