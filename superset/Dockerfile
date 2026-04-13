# change this to apache/superset:5.0.0 or whatever version you want to build from;
# otherwise the default is the latest commit on GitHub master branch
FROM apache/superset:6.0.0

USER root

# Install packages using uv into the virtual environment
RUN . /app/.venv/bin/activate && \
    uv pip install "apache-superset[trino]"

# Switch back to the superset user
USER superset

CMD ["/app/docker/entrypoints/run-server.sh"]
