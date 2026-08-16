# Build:  podman build -t drumtab .
# Run:    podman run --rm -v "$PWD/out:/work/out:Z" drumtab \
#             "https://youtu.be/..." -o out/song
#
# CPU-only image. For CUDA, swap the base for a CUDA runtime and install the
# matching torch wheel; on a Mac run natively (MPS) rather than in a container.
FROM registry.access.redhat.com/ubi9/python-312:latest

USER 0
RUN dnf install -y ffmpeg-free && dnf clean all
USER 1001

WORKDIR /work
COPY --chown=1001:0 . /work

# Base pipeline + the pytorch ADT backend + MusicXML export.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[adt,notation]"

# Model weights (Demucs + ADTOF) download on first run and cache in the volume.
ENV DEMUCS_MODELS=/work/.cache/demucs \
    TORCH_HOME=/work/.cache/torch

ENTRYPOINT ["drumtab"]
CMD ["--help"]
