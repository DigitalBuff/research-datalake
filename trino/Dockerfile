# Lightweight Trino Distribution
# Based on: https://dev.to/resurfacelabs/building-a-lightweight-trino-distribution-54h7
FROM eclipse-temurin:25-jdk-alpine-3.23

# Install required packages
RUN apk add --no-cache wget python3 bash gcompat apache2-utils

# Create and switch to non-root user
RUN addgroup -S runtime && \
    adduser -S -H -G runtime runtime && \
    mkdir -p /opt/trino && \
    chown runtime:runtime /opt/trino
USER runtime
WORKDIR /tmp

# Download and configure Trino
# Do as one big step to reduce container size!
RUN wget --quiet https://github.com/trinodb/trino/releases/download/479/trino-server-core-479.tar.gz && \
    tar -xf trino-server-core-479.tar.gz && \
    cp -R ./trino-server-core-479/* /opt/trino && \
    mkdir -p /tmp/keep-plugins && \
    cp -R /opt/trino/plugin/password-authenticators /tmp/keep-plugins/ && \
    rm -rf /opt/trino/plugin/* && \
    cp -R /tmp/keep-plugins/password-authenticators /opt/trino/plugin/ && \
    rm -rf /tmp/trino-server-core-479/* && \
    rm -rf /tmp/trino-server-core-479.tar.gz && \
    wget --quiet https://github.com/trinodb/trino/releases/download/479/trino-iceberg-479.zip && \
    unzip trino-iceberg-479.zip && \
    mkdir /opt/trino/plugin/iceberg && \
    cp -R ./trino-iceberg-479/* /opt/trino/plugin/iceberg && \
    rm -rf /tmp/trino-iceberg-479/* && \
    rm -rf /tmp/trino-iceberg-479.zip && \
    rm -rf /tmp/keep-plugins

# Switch back to root to copy configuration
USER root

# Copy custom configuration
COPY --chown=runtime:runtime etc /opt/trino/etc
COPY --chown=runtime:runtime docker-entrypoint.sh /opt/trino/docker-entrypoint.sh
RUN chmod +x /opt/trino/docker-entrypoint.sh

# Create data directory
RUN mkdir -p /data/trino && chown runtime:runtime /data/trino

# Switch back to runtime user
USER runtime

# Expose Trino port
EXPOSE 8080

ENTRYPOINT ["/opt/trino/docker-entrypoint.sh"]
