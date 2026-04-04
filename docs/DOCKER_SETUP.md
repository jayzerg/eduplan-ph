# EduPlan PH - Docker Setup Guide

Complete instructions for containerizing and running the EduPlan PH Streamlit application using Docker.

## Prerequisites

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher (included with Docker Desktop)
- **OpenRouter API Key**: Get your free key at [https://openrouter.ai/keys](https://openrouter.ai/keys)

Verify installation:
```bash
docker --version
docker compose version
```

## Quick Start

### Option 1: Using Docker Compose (Recommended)

1. **Clone the repository** (if not already done):
   ```bash
   git clone <your-repo-url>
   cd eduplan-ph
   ```

2. **Create environment file**:
   ```bash
   cp .env.template .env
   ```

3. **Edit `.env` file** and add your OpenRouter API key:
   ```bash
   nano .env  # or use your preferred editor
   ```
   
   Update the line:
   ```
   OPENROUTER_API_KEY=sk-or-v1-YOUR_ACTUAL_API_KEY_HERE
   ```

4. **Build and start the container**:
   ```bash
   docker compose up --build -d
   ```

5. **Access the application**:
   Open your browser and navigate to: `http://localhost:8501`

6. **View logs**:
   ```bash
   docker compose logs -f
   ```

7. **Stop the application**:
   ```bash
   docker compose down
   ```

### Option 2: Using Docker Directly

1. **Create environment file**:
   ```bash
   cp .env.template .env
   # Edit .env with your API key
   ```

2. **Build the Docker image**:
   ```bash
   docker build -t eduplan-ph:latest .
   ```

3. **Run the container**:
   ```bash
   docker run -d \
     --name eduplan-ph-app \
     -p 8501:8501 \
     --env-file .env \
     -v eduplan_cache_data:/app \
     --restart unless-stopped \
     eduplan-ph:latest
   ```

4. **Access the application**:
   Open your browser and navigate to: `http://localhost:8501`

5. **View logs**:
   ```bash
   docker logs -f eduplan-ph-app
   ```

6. **Stop the container**:
   ```bash
   docker stop eduplan-ph-app
   docker rm eduplan-ph-app
   ```

## Configuration Files Overview

### Dockerfile
The `Dockerfile` creates an optimized multi-stage build:
- **Base Image**: Python 3.9-slim for compatibility and small size
- **System Dependencies**: Includes `libfontconfig1` and `fonts-liberation` for PDF/DOCX generation
- **Security**: Runs as non-root user (`appuser`)
- **Optimization**: Copies `requirements.txt` first for better layer caching
- **Health Check**: Built-in health monitoring endpoint
- **Volume Support**: Configured for SQLite cache persistence

### docker-compose.yml
Manages the complete container setup:
- **Service Definition**: Builds from Dockerfile with production target
- **Port Mapping**: Exposes port 8501 (Streamlit default)
- **Environment Variables**: Loads from `.env` file
- **Persistent Storage**: Named volume for cache database
- **Resource Limits**: Configurable CPU and memory constraints
- **Networking**: Dedicated bridge network
- **Logging**: Rotating log files (10MB max, 3 files)

### .dockerignore
Excludes unnecessary files from the Docker build context:
- Git files and documentation
- Test files and coverage reports
- Python cache and bytecode
- Environment files (security)
- SQLite database files (mounted as volumes)
- IDE and editor files

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key | `sk-or-v1-...` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `STREAMLIT_SERVER_PORT` | Streamlit server port | `8501` |
| `STREAMLIT_SERVER_ADDRESS` | Server bind address | `0.0.0.0` |
| `STREAMLIT_BROWSER_GATHER_USAGE_STATS` | Disable usage stats | `false` |
| `CACHE_DB_PATH` | Cache database path | `eduplan_cache.db` |
| `LOG_LEVEL` | Application log level | `INFO` |
| `DEBUG_MODE` | Enable debug mode | `false` |

## Data Persistence

### SQLite Cache Database

The application uses SQLite for caching validated lesson plans. To ensure data persists across container restarts:

**With Docker Compose** (automatic):
```yaml
volumes:
  - eduplan_cache_data:/app
```

**With Docker CLI**:
```bash
-v eduplan_cache_data:/app
```

The named volume `eduplan_cache_data` stores the `eduplan_cache.db` file in `/app/`.

### Managing Persistent Data

**View volume contents**:
```bash
docker volume inspect eduplan-ph-cache-data
```

**Backup cache data**:
```bash
docker run --rm \
  -v eduplan-ph-cache-data:/source \
  -v $(pwd):/backup \
  alpine tar czf /backup/eduplan-cache-backup.tar.gz -C /source .
```

**Restore cache data**:
```bash
docker run --rm \
  -v eduplan-ph-cache-data:/dest \
  -v $(pwd):/backup \
  alpine tar xzf /backup/eduplan-cache-backup.tar.gz -C /dest
```

**Remove persistent data** (⚠️ Warning: This deletes all cached data):
```bash
docker compose down -v
# or
docker volume rm eduplan-ph-cache-data
```

## Networking

### Default Configuration

The application runs on a dedicated bridge network:
- **Network Name**: `eduplan-ph-network`
- **Container Port**: 8501
- **Host Port**: 8501 (configurable)

### Custom Port Mapping

To use a different host port:

**Docker Compose** (edit `docker-compose.yml`):
```yaml
ports:
  - "8080:8501"  # Host:Container
```

**Docker CLI**:
```bash
-p 8080:8501
```

Then access at: `http://localhost:8080`

### Access from Other Containers

Containers on the same network can access EduPlan PH at:
```
http://eduplan-ph-app:8501
```

## Advanced Configuration

### Resource Limits

Adjust resource constraints in `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

### Production Deployment

For production environments:

1. **Use specific image tags** instead of `latest`:
   ```bash
   docker build -t eduplan-ph:1.0.0 .
   ```

2. **Enable container restart policies**:
   ```yaml
   restart: always
   ```

3. **Use external secrets management** instead of `.env` files

4. **Configure reverse proxy** (nginx, traefik) for SSL/TLS

5. **Set up monitoring and alerting** using the health check endpoint:
   ```
   http://localhost:8501/_stcore/health
   ```

### Development Mode

For local development with live reloading:

1. **Mount source code as volume**:
   ```yaml
   volumes:
     - .:/app
     - eduplan_cache_data:/app/cache
   ```

2. **Enable Streamlit watcher**:
   Add to `.env`:
   ```
   STREAMLIT_SERVER_HEADLESS=true
   ```

3. **Run without detached mode** to see logs:
   ```bash
   docker compose up --build
   ```

## Troubleshooting

### Container Won't Start

**Check logs**:
```bash
docker compose logs
# or
docker logs eduplan-ph-app
```

**Common issues**:
- Missing or invalid `OPENROUTER_API_KEY`
- Port already in use: Change host port mapping
- Permission errors: Ensure proper volume permissions

### Application Returns Errors

**Verify API key**:
```bash
docker compose exec eduplan-ph env | grep OPENROUTER
```

**Test connectivity**:
```bash
docker compose exec eduplan-ph curl -I http://localhost:8501/_stcore/health
```

### Cache Database Issues

**Reset cache** (delete volume):
```bash
docker compose down -v
docker compose up -d
```

**Check database file**:
```bash
docker compose exec eduplan-ph ls -la /app/*.db
```

### Performance Issues

**Monitor resource usage**:
```bash
docker stats eduplan-ph-app
```

**Increase resource limits** in `docker-compose.yml`

## Common Commands Reference

```bash
# Build and start
docker compose up --build -d

# Stop application
docker compose down

# View logs
docker compose logs -f

# Restart application
docker compose restart

# Rebuild image
docker compose build --no-cache

# Access container shell
docker compose exec eduplan-ph bash

# Run tests inside container
docker compose exec eduplan-ph python -m pytest tests/

# Clean up everything
docker compose down -v --rmi all
```

## Security Considerations

1. **Never commit `.env` files** to version control
2. **Use strong API keys** and rotate regularly
3. **Run as non-root user** (configured by default)
4. **Limit exposed ports** to only what's necessary
5. **Use HTTPS** in production with a reverse proxy
6. **Regular updates**: Keep base images and dependencies updated

## Support

For issues or questions:
- Check the application logs
- Review the [CHANGELOG.md](CHANGELOG.md) for recent changes
- Consult the [README.md](README.md) for general information
- Open an issue on the GitHub repository
