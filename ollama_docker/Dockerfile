FROM ollama/ollama

# Copying the initialization script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Overriding the default entrypoint
ENTRYPOINT ["/entrypoint.sh"]