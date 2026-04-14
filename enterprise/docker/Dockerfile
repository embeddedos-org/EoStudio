FROM python:3.12-slim AS base
LABEL maintainer="embeddedos-org" description="Design Environment — EoS Enterprise"

WORKDIR /app
COPY pyproject.toml README.md ./
COPY eostudio/ eostudio/
RUN pip install --no-cache-dir -e ".[dev]"

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import eostudio; print('ok')" || exit 1
CMD ["python", "-m", "eostudio.cli.main", "launch"]
