"""
HTTP server for exposing Prometheus metrics.
Runs in a separate thread alongside the worker.
"""

import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import threading

logger = logging.getLogger(__name__)

METRICS_PORT = int(__import__('os').getenv('METRICS_PORT', '8006'))


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for metrics endpoint."""
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(generate_latest())
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy", "service": "worker-service"}')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Override to reduce noise in logs."""
        # Only log errors
        if '404' not in args:
            logger.debug(f"Metrics request: {format % args}")


def start_metrics_server():
    """Start the metrics HTTP server in a background thread."""
    server = HTTPServer(('0.0.0.0', METRICS_PORT), MetricsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"📊 Metrics server started on port {METRICS_PORT}")
    return server

