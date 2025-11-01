# Deployment Directory

This directory contains docker-compose files organized by environment.

## Structure

```
deployment/
├── dev/          # Development docker-compose files (build from local)
│   └── .env      # Development environment variables
├── prod/         # Production docker-compose files (pull from Docker Hub)
│   └── .env      # Production environment variables
```

## Quick Start

### Development
```bash
cd deployment/dev
# See dev/README.md for details
```

### Production
```bash
cd deployment/prod
# See prod/README.md for details
```

## Environment Variables

Create separate `.env` files in both `dev/` and `prod/` directories with the appropriate environment variables for each environment.

See `env.example` in the parent `SelfLearning/` directory for required variables.

