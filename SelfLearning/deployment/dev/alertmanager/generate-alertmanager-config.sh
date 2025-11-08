#!/bin/bash
# Generate alertmanager.yml from environment variables
# This script reads from .env and generates alertmanager.yml

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../../.env"
OUTPUT_FILE="${SCRIPT_DIR}/alertmanager.yml"

# Source .env file if it exists
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# Default values
SMTP_HOST=${ALERTMANAGER_SMTP_HOST:-smtp.gmail.com}
SMTP_PORT=${ALERTMANAGER_SMTP_PORT:-587}
SMTP_FROM=${ALERTMANAGER_SMTP_FROM:-dev@adtechgrowthpartners.com}
SMTP_USERNAME=${ALERTMANAGER_SMTP_USERNAME:-dev@adtechgrowthpartners.com}
SMTP_PASSWORD=${ALERTMANAGER_SMTP_PASSWORD:-}
SMTP_REQUIRE_TLS=${ALERTMANAGER_SMTP_REQUIRE_TLS:-true}
ALERT_EMAIL=${ALERTMANAGER_ALERT_EMAIL:-dev@adtechgrowthpartners.com}

# Generate alertmanager.yml
cat > "$OUTPUT_FILE" << EOF
global:
  resolve_timeout: 5m
  
  # SMTP Configuration
  smtp_smarthost: '${SMTP_HOST}:${SMTP_PORT}'
  smtp_from: '${SMTP_FROM}'
  smtp_auth_username: '${SMTP_USERNAME}'
  smtp_auth_password: '${SMTP_PASSWORD}'
  smtp_require_tls: ${SMTP_REQUIRE_TLS}

# Templates for alert notifications
templates:
  - '/etc/alertmanager/*.tmpl'

# Route tree for alerts
route:
  receiver: 'default-receiver'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  routes:
    # Critical alerts route immediately to critical-receiver
    - match:
        severity: critical
      receiver: 'critical-receiver'
      continue: true
      group_wait: 0s
    
    # Warning alerts
    - match:
        severity: warning
      receiver: 'warning-receiver'
      continue: true

# Inhibit rules (suppress certain alerts when others are firing)
inhibit_rules:
  # Don't alert about high connections if DB is down
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname']

# Receivers
receivers:
  # Default receiver (for unmatched alerts)
  - name: 'default-receiver'
    email_configs:
      - to: '${ALERT_EMAIL}'
        headers:
          Subject: '⚠️ Alert: {{ .GroupLabels.alertname }}'
        html: |
          <h2>Alert Details</h2>
          <table border="1" cellpadding="5" cellspacing="0">
            <tr><td><strong>Alert:</strong></td><td>{{ .GroupLabels.alertname }}</td></tr>
            <tr><td><strong>Severity:</strong></td><td>{{ .CommonLabels.severity }}</td></tr>
            <tr><td><strong>Service:</strong></td><td>{{ .CommonLabels.service }}</td></tr>
            <tr><td><strong>Status:</strong></td><td>{{ .Status }}</td></tr>
            <tr><td><strong>Started:</strong></td><td>{{ .StartsAt }}</td></tr>
          </table>
          <h3>Description</h3>
          <p>{{ range .Alerts }}{{ .Annotations.description }}{{ end }}</p>
          <h3>Labels</h3>
          <ul>
            {{ range .CommonLabels.SortedPairs }}
            <li><strong>{{ .Name }}:</strong> {{ .Value }}</li>
            {{ end }}
          </ul>
        send_resolved: true
  
  # Critical alerts receiver
  - name: 'critical-receiver'
    email_configs:
      - to: '${ALERT_EMAIL}'
        headers:
          Subject: '🚨 CRITICAL: {{ .GroupLabels.alertname }}'
        html: |
          <h2 style="color: red;">🚨 CRITICAL ALERT</h2>
          <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
            <tr style="background-color: #ffcccc;">
              <td><strong>Alert:</strong></td>
              <td><strong>{{ .GroupLabels.alertname }}</strong></td>
            </tr>
            <tr>
              <td><strong>Severity:</strong></td>
              <td style="color: red;"><strong>CRITICAL</strong></td>
            </tr>
            <tr>
              <td><strong>Service:</strong></td>
              <td>{{ .CommonLabels.service }}</td>
            </tr>
            <tr>
              <td><strong>Status:</strong></td>
              <td>{{ .Status }}</td>
            </tr>
            <tr>
              <td><strong>Started:</strong></td>
              <td>{{ .StartsAt }}</td>
            </tr>
          </table>
          <h3>Description</h3>
          <p style="font-size: 14px;">{{ range .Alerts }}{{ .Annotations.description }}{{ end }}</p>
          <h3>Summary</h3>
          <p style="font-size: 14px;">{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}</p>
          <h3>Labels</h3>
          <ul>
            {{ range .CommonLabels.SortedPairs }}
            <li><strong>{{ .Name }}:</strong> {{ .Value }}</li>
            {{ end }}
          </ul>
          <hr>
          <p style="color: #666; font-size: 12px;">
            This is a critical alert requiring immediate attention.
          </p>
        send_resolved: true
  
  # Warning alerts receiver
  - name: 'warning-receiver'
    email_configs:
      - to: '${ALERT_EMAIL}'
        headers:
          Subject: '⚠️ Warning: {{ .GroupLabels.alertname }}'
        html: |
          <h2 style="color: orange;">⚠️ Warning Alert</h2>
          <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
            <tr style="background-color: #fff4cc;">
              <td><strong>Alert:</strong></td>
              <td><strong>{{ .GroupLabels.alertname }}</strong></td>
            </tr>
            <tr>
              <td><strong>Severity:</strong></td>
              <td style="color: orange;"><strong>WARNING</strong></td>
            </tr>
            <tr>
              <td><strong>Service:</strong></td>
              <td>{{ .CommonLabels.service }}</td>
            </tr>
            <tr>
              <td><strong>Status:</strong></td>
              <td>{{ .Status }}</td>
            </tr>
            <tr>
              <td><strong>Started:</strong></td>
              <td>{{ .StartsAt }}</td>
            </tr>
          </table>
          <h3>Description</h3>
          <p style="font-size: 14px;">{{ range .Alerts }}{{ .Annotations.description }}{{ end }}</p>
          <h3>Summary</h3>
          <p style="font-size: 14px;">{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}</p>
          <h3>Labels</h3>
          <ul>
            {{ range .CommonLabels.SortedPairs }}
            <li><strong>{{ .Name }}:</strong> {{ .Value }}</li>
            {{ end }}
          </ul>
          <hr>
          <p style="color: #666; font-size: 12px;">
            This is a warning alert. Please review and take action if necessary.
          </p>
        send_resolved: true
EOF

echo "✅ Generated alertmanager.yml from .env variables"
echo "📁 Output: $OUTPUT_FILE"

