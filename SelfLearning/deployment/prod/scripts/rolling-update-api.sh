#!/usr/bin/env bash
#
# Perform a rolling update of the API containers defined in docker-compose.api.yml.
# The script updates one container at a time, waiting for it to become healthy
# before proceeding to the next so that at least one instance stays available.

if [ -z "${BASH_VERSION:-}" ]; then
    exec /usr/bin/env bash "$0" "$@"
fi

set -euo pipefail

COMPOSE_FILE="/home/amit/deployment/v10/docker-compose.api.yml"

if command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE_BIN="docker-compose"
elif command -v docker >/dev/null 2>&1; then
    DOCKER_COMPOSE_BIN="docker compose"
else
    echo "docker-compose or the docker compose plugin is required but not found." >&2
    exit 1
fi

compose_cmd() {
    # shellcheck disable=SC2086
    $DOCKER_COMPOSE_BIN -f "$COMPOSE_FILE" "$@"
}

declare -A SERVICE_CONTAINER_MAP=(
    ["api-service"]="fyi-widget-api"
    ["api-service-2"]="fyi-widget-api-2"
)

wait_for_health() {
    local container="$1"
    local timeout="${2:-300}"
    local interval=5
    local elapsed=0

    echo "Waiting for container '${container}' to report healthy status..."

    while true; do
        local status
        status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}unknown{{end}}' "$container" 2>/dev/null || echo "missing")"

        if [[ "$status" == "healthy" ]]; then
            echo "✅ ${container} is healthy."
            break
        fi

        if [[ "$status" == "missing" ]]; then
            echo "Container '${container}' not found. Waiting for it to appear..." >&2
        fi

        if (( elapsed >= timeout )); then
            echo "❌ Timed out waiting for '${container}' to become healthy (last status: ${status})." >&2
            exit 1
        fi

        sleep "$interval"
        elapsed=$((elapsed + interval))
    done
}

ensure_other_services_healthy() {
    local current_service="$1"
    for peer_service in "${!SERVICE_CONTAINER_MAP[@]}"; do
        if [[ "$peer_service" == "$current_service" ]]; then
            continue
        fi

        local container="${SERVICE_CONTAINER_MAP[$peer_service]}"
        local status
        local container_exists
        container_exists="$(docker ps -a --format '{{.Names}}' | grep -q "^${container}$" && echo "yes" || echo "no")"
        
        if [[ "$container_exists" == "no" ]]; then
            echo "⚠️  Warning: peer container '${container}' does not exist. Continuing, but zero downtime is not guaranteed." >&2
            continue
        fi
        
        status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container" 2>/dev/null || echo "missing")"

        case "$status" in
            healthy)
                echo "✅ Peer container '${container}' is healthy."
                continue
                ;;
            missing)
                echo "⚠️  Warning: peer container '${container}' status is missing. Continuing, but zero downtime is not guaranteed." >&2
                ;;
            starting)
                echo "⏳ Waiting for peer container '${container}' to become healthy before updating ${current_service}..."
                wait_for_health "$container" 180
                ;;
            running)
                # Container is running but health check hasn't passed yet - wait for it
                echo "⏳ Peer container '${container}' is running, waiting for health check..."
                wait_for_health "$container" 180
                ;;
            *)
                echo "❌ Peer container '${container}' is in status '${status}'. Aborting rolling update to avoid downtime." >&2
                exit 1
                ;;
        esac
    done
}

update_service() {
    local service="$1"
    local container="${SERVICE_CONTAINER_MAP[$service]}"

    echo ""
    echo "=== Updating ${service} (${container}) ==="
    ensure_other_services_healthy "$service"

    echo "Pulling latest image for ${service}..."
    compose_cmd pull "$service"

    echo "Recreating ${service} with force-recreate..."
    # Try to recreate with force-recreate first
    local recreate_output
    recreate_output="$(compose_cmd up -d --force-recreate --no-deps "$service" 2>&1)" || {
        # If that fails, check for name conflicts with any of our containers
        echo "Force-recreate failed. Checking for container name conflicts..."
        for other_container in "${SERVICE_CONTAINER_MAP[@]}"; do
            # Remove any conflicting container mentioned in the error
            if echo "$recreate_output" | grep -q "${other_container}"; then
                echo "Removing conflicting container '${other_container}'..."
                docker rm -f "$other_container" 2>/dev/null || true
            fi
        done
        # Also remove the container we're updating as a fallback
        docker rm -f "$container" 2>/dev/null || true
        echo "Retrying recreation of ${service}..."
        compose_cmd up -d --no-deps "$service"
    }

    wait_for_health "$container"
}

cleanup_orphaned_containers() {
    echo "Checking for orphaned containers..."
    local current_project
    current_project="$(basename "$(dirname "$COMPOSE_FILE")")"
    
    for container in "${SERVICE_CONTAINER_MAP[@]}"; do
        if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
            # Check if container is managed by current compose project
            local container_project
            container_project="$(docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' "$container" 2>/dev/null || echo "")"
            local container_status
            container_status="$(docker inspect --format '{{.State.Status}}' "$container" 2>/dev/null || echo "missing")"
            
            # Remove if it's from a different project (or has no project label) AND is not running
            # This preserves healthy containers from other projects until we're ready to replace them
            if [[ "$container_status" != "running" ]] && ([[ -z "$container_project" ]] || [[ "$container_project" != "$current_project" ]]); then
                echo "Removing stopped/orphaned container '${container}' (project: ${container_project:-none}, current: ${current_project}, status: ${container_status})..."
                docker rm -f "$container" 2>/dev/null || true
            elif [[ -n "$container_project" ]] && [[ "$container_project" != "$current_project" ]]; then
                echo "⚠️  Container '${container}' exists from project '${container_project}' but current is '${current_project}'. Will be replaced during update."
            fi
        fi
    done
}

main() {
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        echo "Compose file '$COMPOSE_FILE' not found. Update the COMPOSE_FILE path in the script." >&2
        exit 1
    fi

    echo "Starting rolling update using compose file: $COMPOSE_FILE"
    
    cleanup_orphaned_containers

    update_service "api-service"
    update_service "api-service-2"

    echo ""
    echo "🎉 Rolling update complete. Both API instances are healthy."
}

main "$@"

