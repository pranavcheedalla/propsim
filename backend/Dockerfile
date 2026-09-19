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

# data/propsim.db is a committed snapshot (see data/fetch_real_data.py
# and data/fetch_next_games.py), not regenerated at build time: nba_api's
# stats.nba.com endpoint is known to block requests from cloud/datacenter
# IP ranges, which would make the build fail unpredictably on a host
# like Render/Fly/Railway. Refresh the snapshot from a normal network
# (it works fine locally) and commit the updated file to update prod.

EXPOSE 8000
WORKDIR /app/backend
# $PORT is set by most PaaS hosts (Render, etc.) at runtime; falls back
# to 8000 for local `docker run`/docker-compose.
CMD python3 -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
