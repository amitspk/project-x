#!/usr/bin/env bash
#
# Perform a rolling update of the API containers defined in docker-compose.api.yml.
# The script updates one container at a time, waiting for it to become healthy
# before proceeding to the next so that at least one instance stays available.

if [ -z "${BASH_VERSION:-}" ]; then
    exec /usr/bin/env bash "$0" "$@"
fi

set -euo pipefail

COMPOSE_FILE="/home/amit/deployment/v7/docker-compose.api.yml"

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
    for service in "${!SERVICE_CONTAINER_MAP[@]}"; do
        if [[ "$service" == "$current_service" ]]; then
            continue
        fi

        local container="${SERVICE_CONTAINER_MAP[$service]}"
        local status
        status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' "$container" 2>/dev/null || echo "missing")"

        case "$status" in
            healthy)
                continue
                ;;
            missing)
                echo "⚠️  Warning: peer container '${container}' is not running. Continuing, but zero downtime is not guaranteed." >&2
                ;;
            starting)
                echo "⏳ Waiting for peer container '${container}' to become healthy before updating ${current_service}..."
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

    echo "Recreating ${service}..."
    compose_cmd up -d --no-deps "$service"

    wait_for_health "$container"
}

main() {
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        echo "Compose file '$COMPOSE_FILE' not found. Update the COMPOSE_FILE path in the script." >&2
        exit 1
    fi

    echo "Starting rolling update using compose file: $COMPOSE_FILE"

    update_service "api-service"
    update_service "api-service-2"

    echo ""
    echo "🎉 Rolling update complete. Both API instances are healthy."
}

main "$@"

