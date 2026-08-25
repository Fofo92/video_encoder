ARG CCEXTRACTOR_BASE_IMAGE=scratch

FROM ${CCEXTRACTOR_BASE_IMAGE}

ARG CCEXTRACTOR_VERSION
ARG CCEXTRACTOR_COMMIT

LABEL org.opencontainers.image.title="video_encoder CCExtractor OCR français"
LABEL org.opencontainers.image.description="CCExtractor avec Tesseract et modèle français"
LABEL org.opencontainers.image.version="${CCEXTRACTOR_VERSION}"
LABEL org.opencontainers.image.revision="${CCEXTRACTOR_COMMIT}"
LABEL org.opencontainers.image.source="https://github.com/CCExtractor/ccextractor"

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
  tesseract-ocr-fra \
  && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["/ccextractor"]
