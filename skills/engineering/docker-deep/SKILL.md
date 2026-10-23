---
name: docker-deep
description: Use when building, hardening, or debugging Docker containers
  on an authorized engineering task. Covers multi-stage Dockerfiles, layer
  caching, minimal base images, non-root users, Compose for multi-service
  stacks, volumes and networks, image scanning, resource limits, and
  troubleshooting with logs, exec, and inspect. Use when containerizing an
  app, shrinking an image, fixing a broken build, or reviewing a
  Dockerfile for security.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [linux-hardening, git-workflows]
tools:
  - name: Docker
    version: 27
---

Docker packages an application and its dependencies into a portable
image that runs the same everywhere. This skill goes beyond `docker
run`: writing efficient Dockerfiles, keeping images small and
non-root, orchestrating stacks with Compose, and debugging containers
like a professional. All commands target Docker 27 with BuildKit.

## Quick Workflow

1. Write a multi-stage Dockerfile: build in one stage, ship only the
   runtime artifacts in the final stage.
2. Order instructions from least-changing to most-changing to maximize
   layer cache hits.
3. Use a minimal base image and run the app as a non-root user.
4. Build with `docker build`, tag explicitly, and scan the image.
5. Define multi-service stacks in `compose.yaml`, with named volumes
   and isolated networks.
6. Set memory and CPU limits so one container cannot starve the host.
7. Debug with `docker logs`, `docker exec`, and `docker inspect`,
   in that order.
8. Prune aggressively on dev machines, never with `-a` on shared
   build hosts without checking.

## 1. Multi-stage Dockerfile

```bash
mkdir docker-demo && cd docker-demo
cat > Dockerfile <<'EOF'
# Stage 1: build the Go binary
FROM golang:1.23-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /app/server .

# Stage 2: minimal runtime image
FROM alpine:3.20
RUN adduser -D -u 10001 appuser
COPY --from=build /app/server /usr/local/bin/server
USER appuser
EXPOSE 8080
ENTRYPOINT ["server"]
EOF

# BuildKit build with a named tag (never rely on :latest in production)
DOCKER_BUILDKIT=1 docker build -t demo-server:1.0.0 .
docker images demo-server
```

Multi-stage builds keep compilers, source, and caches out of the
final image. The result here is a ~15 MB static binary on Alpine
instead of a ~1 GB Go toolchain image.

## 2. Layer caching done right

```bash
cat > Dockerfile.node <<'EOF'
FROM node:22-alpine
WORKDIR /app
# Copy dependency manifests FIRST so npm install is cached
# until dependencies actually change
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY . .
RUN npm run build
USER node
CMD ["node", "dist/index.js"]
EOF

# Watch the cache work: second build reuses every layer until COPY . .
docker build -f Dockerfile.node -t demo-node:1.0.0 . 2>&1 | tail -8
```

Put `COPY package.json` before `COPY .` so editing application code
does not reinstall dependencies. Add a `.dockerignore` so build
context stays small:

```bash
cat > .dockerignore <<'EOF'
node_modules
.git
.gitignore
*.md
dist
coverage
.env
EOF
```

## 3. Compose for multi-service stacks

```bash
cat > compose.yaml <<'EOF'
services:
  web:
    build: .
    ports:
      - "8080:8080"
    environment:
      DATABASE_URL: postgres://app:${DB_PASSWORD}@db:5432/appdb
    depends_on:
      db:
        condition: service_healthy
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
    networks: [frontend, backend]

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: appdb
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 5s
      timeout: 3s
      retries: 10
    networks: [backend]

volumes:
  pgdata:

networks:
  frontend:
  backend:
EOF

# Secrets come from the environment, never from the file
export DB_PASSWORD="$(openssl rand -hex 16)"
docker compose up -d
docker compose ps
docker compose logs -f web
```

Compose gives each project isolated networks by default. The `web`
service can reach `db` at hostname `db`; nothing else on the host
can. Healthchecks plus `depends_on` stop the app from starting before
the database accepts connections.

## 4. Volumes, networks, and inspection

```bash
# Named volume vs bind mount: volumes for data, binds for config/code
docker volume create appdata
docker run -d --name demo -v appdata:/data alpine:3.20 sleep 3600
docker volume inspect appdata

# Networks: put the database on an internal network only
docker network create --internal backend-only
docker network connect backend-only demo

# Inspect anything when behavior is unclear
docker inspect demo --format '{{json .NetworkSettings.Networks}}' | head -c 400; echo
docker inspect demo --format '{{.Config.User}} {{.HostConfig.Memory}}'
```

Use volumes for data that must survive container replacement, bind
mounts for injecting config or live code during development, and
`tmpfs` mounts for scratch space that must never hit disk.

## 5. Scanning and hardening

```bash
# Scan the image for known CVEs in OS packages and app dependencies
docker scout cves demo-server:1.0.0 2>/dev/null || \
  echo "docker scout needs a Docker Hub login; use trivy instead"

# Trivy alternative (install once, scan offline-capable)
trivy image --severity HIGH,CRITICAL demo-server:1.0.0 | head -30

# Hardening checklist for the Dockerfile
grep -E '^(USER|HEALTHCHECK)' Dockerfile || echo "MISSING: USER and HEALTHCHECK"

# Drop capabilities and make the filesystem read-only at runtime
docker run -d --name hardened \
  --read-only --tmpfs /tmp \
  --cap-drop ALL --cap-add NET_BIND_SERVICE \
  --user 10001 \
  --memory 256m --cpus 0.5 \
  demo-server:1.0.0
```

Harden every production container: non-root user, read-only root
filesystem, dropped capabilities, resource limits, and no `--privileged`
ever. Scan images in CI and fail the build on new CRITICAL findings.

## 6. Debugging like a professional

```bash
# 1. Logs first: what did the app say before it died
docker logs --tail 100 demo
docker logs -f --since 10m demo

# 2. Exec into the running container to look around
docker exec -it demo sh
# inside: check listening ports, env, files
# netstat -tlnp 2>/dev/null || ss -tlnp
# env | sort

# 3. Inspect the container's full configuration
docker inspect demo | grep -A5 -i '"env"'

# Container keeps exiting: run it interactively to see the error
docker run --rm -it demo-server:1.0.0 sh

# Show resource usage live
docker stats --no-stream
```

When a container exits immediately, the cause is almost always in the
last 20 lines of `docker logs`: a missing env var, a bad config path,
or a permission error on a mounted volume.

## 7. Cleanup and disk hygiene

```bash
# Safe cleanup: stopped containers, unused networks, dangling images
docker system prune

# Show what is eating disk
docker system df

# Remove everything unused (CAREFUL on shared hosts)
# docker system prune -a --volumes
```

## Edge cases

- Build is slow because the context is huge. Check `.dockerignore`;
  a stray `node_modules` or `.git` directory multiplies build time
  and can leak secrets into image layers.
- `COPY --from=build` fails with "not found". The source path must
  exist in the named stage; stage names are case-sensitive and a
  typo silently refers to a different stage.
- App binds to `localhost` inside the container and is unreachable.
  Bind to `0.0.0.0` inside containers; `localhost` in a container is
  the container itself, not the host.
- Permission denied on a mounted volume. The container user (UID
  10001) differs from the host file owner; fix with `chown` on the
  host or run the container with `--user $(id -u):$(id -g)` in dev.
- `docker compose up` recreates the database and data is gone. Data
  lives only in named volumes; anonymous volumes and container
  filesystems are ephemeral. Always declare named volumes for
  databases.
- Image works locally but fails on the registry host with "exec
  format error". You built for the wrong architecture (arm64 laptop
  vs amd64 server); build with `--platform linux/amd64`.
- Secrets visible in `docker inspect` or image history. Never use
  `ENV` or build args for secrets; use runtime env files, Docker
  secrets, or a vault integration instead.

## Detection and defender view

For engineering skills this section covers detecting misuse and
misconfiguration. A misconfigured Docker host shows containers
running `--privileged`, the Docker socket mounted inside a container
(`/var/run/docker.sock`, which is root-equivalent on the host),
images running as root, and secrets baked into layers (find them
with `docker history` and layer inspection). Detect misuse by
auditing `docker ps` for privileged flags, scanning images for
CRITICAL CVEs before deployment, and alerting on containers with
host network mode or sensitive host path mounts. Cryptominers and
compromised containers reveal themselves through `docker stats`
(CPU pinned at the limit with no legitimate workload) and unexpected
outbound connections from container networks.

## Key references

- Docker 27 engine docs: https://docs.docker.com/engine/
- Dockerfile reference: https://docs.docker.com/reference/dockerfile/
- Compose specification: https://docs.docker.com/compose/
- CIS Docker Benchmark: https://www.cisecurity.org/benchmark/docker
- CWE-250 (Execution with Unnecessary Privileges): containers
  running as root or privileged.
- CWE-798 (Use of Hard-coded Credentials): secrets in Dockerfiles
  and image layers.
- OWASP Docker Top 10: https://owasp.org/www-project-docker-top-10/
