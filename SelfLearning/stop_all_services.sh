#!/bin/bash

###############################################################################
# Stop All Services Script
###############################################################################

echo "════════════════════════════════════════════════════════════════════"
echo "🛑 Stopping Blog Q&A System - All Services"
echo "════════════════════════════════════════════════════════════════════"
echo ""

docker-compose -f docker-compose.split-services.yml down

echo ""
echo "✅ All services stopped"
echo ""
echo "To start again: ./start_all_services.sh"
echo "To remove data:  docker-compose -f docker-compose.split-services.yml down -v"
echo ""

