# Build context is expected to be the repository root (propsim/), so this
# image can compile the C++ engine and include the python/backtest/data
# packages it imports at runtime.
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY cpp/ cpp/
RUN cd cpp && rm -rf build && mkdir build && cd build \
    && cmake .. -DCMAKE_BUILD_TYPE=Release \
    && make -j"$(nproc)"

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app/cpp/build/*.so cpp/build/
COPY python/ python/
COPY backtest/ backtest/
COPY data/ data/
COPY backend/ backend/

# Pull real NBA data (nba_api, already in requirements.txt) at build
# time so the image is self-contained. Requires network access during
# `docker build`.
RUN cd data && python3 fetch_real_data.py && python3 fetch_next_games.py

EXPOSE 8000
WORKDIR /app/backend
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
