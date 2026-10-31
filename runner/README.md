# NoBluff Runner Image

A minimal, unprivileged Docker image used by the NoBluff controlled verification runner.

## Purpose

The image provides a reproducible, sandboxed Python environment for running isolated
`pytest`-based verification scripts at runtime. Repository source is **not** baked
into the image — it is mounted read-only by the runner at verification time.

## Pinned Versions

| Component | Version |
|---|---|
| Base image | `python:3.11.9-slim-bookworm` |
| pytest | `8.3.5` |

## Build

```bash
docker build -t nobluff-runner:ci runner
```

## Verify the image

```bash
# Check pytest is installed at the pinned version
docker run --rm nobluff-runner:ci python -m pytest --version

# Confirm the container runs as the non-root user 'runner'
docker run --rm nobluff-runner:ci whoami
```

## Security notes

- The container runs as a non-root user (`runner`, UID 10001).
- No repository source, secrets, tokens, or network configuration are embedded in the image.
- Source code is mounted read-only at run time by the orchestrating runner process.
