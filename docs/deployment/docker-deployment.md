# 🐳 Docker Deployment Guide

Complete guide for deploying the Trading System using Docker containers for development, staging, and production environments.

## 📋 Prerequisites

### System Requirements
- **Docker**: 20.10 or higher
- **Docker Compose**: 2.0 or higher
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 20GB free disk space
- **Network**: Internet connection for image downloads

### Optional Tools
- **Docker Desktop**: GUI for container management
- **Portainer**: Web UI for Docker management
- **Docker Registry**: For private image storage

## 🚀 Quick Start with Docker Compose

### 1. Clone Repository

```bash
git clone https://github.com/your-org/trading-system.git
cd trading-system
```

### 2. Environment Configuration

Create environment-specific configuration:

```bash
# For development
cp docker/docker-compose.dev.yml docker-compose.yml

# For production
cp docker/docker-compose.prod.yml docker-compose.yml

# Or use override files
cp docker/docker-compose.override.dev.yml docker-compose.override.yml
```

### 3. Start Services

```bash
# Start all services
docker-compose up -d

# Start with specific services
docker-compose up -d api dashboard websocket

# Start with build
docker-compose up -d --build
```

### 4. Verify Deployment

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f

# Check API health
curl http://localhost:8000/health

# Check dashboard
curl http://localhost:8080/
```

## 🏗️ Docker Architecture

### Service Overview

```
trading-system
├── api              # REST API service
├── dashboard        # Web dashboard
├── websocket        # Real-time data service
├── database         # PostgreSQL (production)
├── redis            # Caching & sessions
├── nginx            # Reverse proxy & load balancer
└── monitoring       # Prometheus & Grafana
```

### Container Images

#### Base Images
- **API Service**: `python:3.11-slim`
- **Dashboard**: `python:3.11-slim`
- **WebSocket**: `python:3.11-slim`
- **Database**: `postgres:15-alpine`
- **Cache**: `redis:7-alpine`
- **Proxy**: `nginx:1.25-alpine`

#### Custom Images
```dockerfile
# API Service Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["python", "-m", "src.interfaces.api.main"]
```

## 📁 Docker Compose Configurations

### Development Configuration

```yaml
# docker/docker-compose.dev.yml
version: '3.8'

services:
  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - TRADING_ENV=development
      - DATABASE_URL=postgresql://trading:password@db:5432/trading_dev
    depends_on:
      - db
    volumes:
      - ../logs:/app/logs
      - ../data:/app/data
    restart: unless-stopped

  dashboard:
    build:
      context: ..
      dockerfile: docker/Dockerfile.dashboard
    ports:
      - "8080:8080"
    environment:
      - TRADING_ENV=development
    depends_on:
      - api
    restart: unless-stopped

  websocket:
    build:
      context: ..
      dockerfile: docker/Dockerfile.websocket
    ports:
      - "8081:8081"
    environment:
      - TRADING_ENV=development
    depends_on:
      - api
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=trading_dev
      - POSTGRES_USER=trading
      - POSTGRES_PASSWORD=password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ../docker/init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Production Configuration

```yaml
# docker/docker-compose.prod.yml
version: '3.8'

services:
  api:
    image: your-registry/trading-api:latest
    environment:
      - TRADING_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - API_SECRET_KEY=${API_SECRET_KEY}
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  dashboard:
    image: your-registry/trading-dashboard:latest
    environment:
      - TRADING_ENV=production
    deploy:
      replicas: 2
    restart: unless-stopped

  websocket:
    image: your-registry/trading-websocket:latest
    environment:
      - TRADING_ENV=production
    deploy:
      replicas: 2
    restart: unless-stopped

  nginx:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ../nginx/nginx.conf:/etc/nginx/nginx.conf
      - ../nginx/ssl:/etc/nginx/ssl
    depends_on:
      - api
      - dashboard
      - websocket
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=${DB_NAME}
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_prod:/var/lib/postgresql/data
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_prod:/data
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
    restart: unless-stopped

volumes:
  postgres_prod:
  redis_prod:
```

## 🔧 Docker Configuration Files

### API Dockerfile

```dockerfile
# docker/Dockerfile.api
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TRADING_ENV=production

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Change ownership
RUN chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Start application
CMD ["python", "-m", "src.interfaces.api.main"]
```

### Nginx Configuration

```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream api_backend {
        server api:8000;
    }

    upstream dashboard_backend {
        server dashboard:8080;
    }

    upstream websocket_backend {
        server websocket:8081;
    }

    server {
        listen 80;
        server_name localhost;

        # API routes
        location /api/ {
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Dashboard routes
        location / {
            proxy_pass http://dashboard_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket routes
        location /ws/ {
            proxy_pass http://websocket_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### Database Initialization

```sql
-- docker/init.sql
-- Database initialization script

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS trading_dev;

-- Switch to trading database
\c trading_dev;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create application user
CREATE USER IF NOT EXISTS trading_app WITH PASSWORD 'app_password';
GRANT ALL PRIVILEGES ON DATABASE trading_dev TO trading_app;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS market_data;
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Grant permissions
GRANT ALL ON SCHEMA market_data TO trading_app;
GRANT ALL ON SCHEMA trading TO trading_app;
GRANT ALL ON SCHEMA analytics TO trading_app;
```

## 🚀 Deployment Strategies

### Development Deployment

```bash
# 1. Build and start development stack
docker-compose -f docker/docker-compose.dev.yml up -d --build

# 2. Run database migrations
docker-compose -f docker/docker-compose.dev.yml exec api python scripts/migrate.py

# 3. Seed development data
docker-compose -f docker/docker-compose.dev.yml exec api python scripts/seed.py

# 4. Check health
curl http://localhost:8000/health
```

### Production Deployment

```bash
# 1. Build production images
docker build -t your-registry/trading-api:latest -f docker/Dockerfile.api .
docker build -t your-registry/trading-dashboard:latest -f docker/Dockerfile.dashboard .
docker build -t your-registry/trading-websocket:latest -f docker/Dockerfile.websocket .

# 2. Push to registry
docker push your-registry/trading-api:latest
docker push your-registry/trading-dashboard:latest
docker push your-registry/trading-websocket:latest

# 3. Deploy with Docker Compose
docker-compose -f docker/docker-compose.prod.yml up -d

# 4. Run database migrations
docker-compose -f docker/docker-compose.prod.yml exec api python scripts/migrate.py

# 5. Verify deployment
curl https://your-domain.com/health
```

### Blue-Green Deployment

```bash
# 1. Deploy new version to blue environment
docker-compose -f docker/docker-compose.blue.yml up -d

# 2. Test blue environment
curl http://blue.your-domain.com/health

# 3. Switch traffic to blue
# Update load balancer configuration

# 4. Keep green environment as rollback option
# docker-compose -f docker/docker-compose.green.yml stop

# 5. Clean up old containers
docker system prune -f
```

## 📊 Monitoring & Logging

### Container Logs

```bash
# View all container logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api

# View last 100 lines
docker-compose logs --tail=100 api

# Follow logs with timestamps
docker-compose logs -f -t api
```

### Container Metrics

```bash
# View container resource usage
docker stats

# View specific container stats
docker stats api dashboard websocket

# Monitor container health
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Log Aggregation

```bash
# Use Docker logging drivers
# docker-compose.yml
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

# Or use external logging
services:
  api:
    logging:
      driver: "syslog"
      options:
        syslog-address: "tcp://logstash:514"
```

## 🔧 Maintenance Tasks

### Database Backup

```bash
# Backup PostgreSQL database
docker-compose exec db pg_dump -U trading trading_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
docker-compose exec -T db psql -U trading trading_prod < backup.sql
```

### Container Updates

```bash
# Update all images
docker-compose pull

# Update specific service
docker-compose pull api
docker-compose up -d api

# Zero-downtime updates
docker-compose up -d --no-deps api
```

### Storage Management

```bash
# Check disk usage
docker system df

# Clean up unused resources
docker system prune -f

# Clean up volumes
docker volume prune -f

# View volume usage
docker volume ls
```

## 🔒 Security Best Practices

### Container Security

```yaml
# docker/docker-compose.prod.yml
services:
  api:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    user: "1000:1000"  # Non-root user
```

### Network Security

```yaml
# Use internal networks
networks:
  internal:
    driver: bridge
    internal: true

services:
  db:
    networks:
      - internal
  api:
    networks:
      - internal
      - external
```

### Secret Management

```yaml
# Use Docker secrets
secrets:
  db_password:
    file: ./secrets/db_password.txt

services:
  db:
    secrets:
      - db_password
```

### SSL/TLS Configuration

```bash
# Generate SSL certificates
openssl req -x509 -newkey rsa:4096 \
  -keyout ssl/private/trading.key \
  -out ssl/certs/trading.crt \
  -days 365 -nodes \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=trading.example.com"

# Configure Nginx for SSL
server {
    listen 443 ssl http2;
    server_name trading.example.com;

    ssl_certificate /etc/nginx/ssl/trading.crt;
    ssl_certificate_key /etc/nginx/ssl/trading.key;

    # SSL security settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
}
```

## 🚨 Troubleshooting

### Common Issues

#### Container Won't Start
```bash
# Check container logs
docker-compose logs api

# Check container status
docker-compose ps

# Inspect container
docker inspect trading-api

# Check resource usage
docker stats
```

#### Database Connection Issues
```bash
# Check database logs
docker-compose logs db

# Test database connection
docker-compose exec db psql -U trading -d trading_prod -c "SELECT version();"

# Check database environment variables
docker-compose exec api env | grep DATABASE
```

#### Network Issues
```bash
# Check network connectivity
docker-compose exec api ping db

# Check exposed ports
docker-compose ps
docker port trading-api

# Inspect networks
docker network ls
docker network inspect trading_default
```

#### Performance Issues
```bash
# Monitor resource usage
docker stats

# Check container limits
docker inspect trading-api | grep -A 10 "Limits"

# Profile application
docker-compose exec api python -m cProfile -s time src/interfaces/api/main.py
```

## 📈 Scaling & High Availability

### Horizontal Scaling

```yaml
# Scale API service
docker-compose up -d --scale api=3

# Scale with Docker Swarm
docker service scale trading_api=5

# Scale with Kubernetes
kubectl scale deployment trading-api --replicas=5
```

### Load Balancing

```yaml
# Use Docker Swarm
version: '3.8'
services:
  api:
    image: trading-api
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
    networks:
      - web

  lb:
    image: dockercloud/haproxy
    links:
      - api
    ports:
      - "80:80"
    networks:
      - web
```

### Database Clustering

```yaml
# PostgreSQL with replication
services:
  db_master:
    image: postgres:15
    environment:
      - POSTGRES_DB=trading
      - POSTGRES_USER=trading
      - REPLICATION_MODE=master
      - REPLICATION_USER=replica
      - REPLICATION_PASSWORD=replica_pass

  db_replica:
    image: postgres:15
    environment:
      - POSTGRES_DB=trading
      - POSTGRES_USER=trading
      - REPLICATION_MODE=slave
      - REPLICATION_HOST=db_master
      - REPLICATION_USER=replica
      - REPLICATION_PASSWORD=replica_pass
```

## 🎯 Best Practices

### Development Workflow
1. **Use multi-stage builds** for smaller production images
2. **Implement health checks** for all services
3. **Use .dockerignore** to exclude unnecessary files
4. **Tag images properly** with version and environment
5. **Test containers locally** before deployment

### Production Considerations
1. **Use production-grade base images** (Alpine Linux)
2. **Implement proper logging** with structured format
3. **Configure resource limits** to prevent resource exhaustion
4. **Use secrets management** for sensitive data
5. **Implement backup strategies** for data persistence

### Monitoring & Alerting
1. **Monitor container health** with health checks
2. **Collect metrics** with Prometheus
3. **Set up alerting** for critical issues
4. **Log aggregation** with ELK stack
5. **Performance monitoring** with APM tools

This Docker deployment guide provides a comprehensive approach to containerizing and deploying the Trading System across different environments with production-grade configurations.
