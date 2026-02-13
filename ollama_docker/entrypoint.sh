#!/bin/bash

# Starts the ollama server in the background
ollama serve &

# Wait the server is ready
sleep 5

# Downloads the specified model in the environment variables of the docker-compose.yml file
echo "Downloading model: $OLLAMA_MODEL..."
ollama pull $OLLAMA_MODEL

echo "Model ready!"

# Wait for the background process (the server) to not close the container
wait