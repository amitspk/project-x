#!/bin/bash

# Final Cleanup Script - Split Services Architecture
# This script removes obsolete services, test files, and consolidates documentation

set -e  # Exit on error

ARCHIVE_DIR="archive/final_cleanup_$(date +%Y%m%d_%H%M%S)"

echo "════════════════════════════════════════════════════════════════════"
echo "🧹 FINAL CLEANUP - Split Services Architecture"
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "This will:"
echo "  • Remove obsolete services (content_processing_service)"
echo "  • Remove test/debug scripts"
echo "  • Remove duplicate/outdated documentation"
echo "  • Keep only production-ready files"
echo ""
echo "Archived files will be moved to: $ARCHIVE_DIR"
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

# Create archive directory
mkdir -p "$ARCHIVE_DIR"

echo ""
echo "Step 1: Archive obsolete services"
echo "─────────────────────────────────────────────────────────────────────"

# Archive content_processing_service (replaced by api_service + worker_service)
if [ -d "content_processing_service" ]; then
    echo "  📦 Archiving content_processing_service/"
    mv content_processing_service "$ARCHIVE_DIR/"
else
    echo "  ℹ️  content_processing_service/ not found (already removed)"
fi

echo ""
echo "Step 2: Remove test and debug scripts"
echo "─────────────────────────────────────────────────────────────────────"

# Python test files
TEST_FILES=(
    "benchmark_architectures.py"
    "test_url_normalization.py"
)

for file in "${TEST_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  🗑️  Removing $file"
        rm "$file"
    fi
done

# Shell test scripts
TEST_SCRIPTS=(
    "cleanup_legacy_files.sh"
    "cleanup_remaining_legacy.sh"
    "test_2_service_architecture.sh"
    "test_split_architecture.sh"
    "test_url_normalization_e2e.sh"
    "verify_extension_ready.sh"
)

for script in "${TEST_SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        echo "  🗑️  Removing $script"
        rm "$script"
    fi
done

# HTML test files
HTML_TEST_FILES=(
    "test_randomization.html"
    "test_search_functionality.html"
    "test_similar_blogs_ui.html"
    "test_ui_integration.html"
)

for file in "${HTML_TEST_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  🗑️  Removing $file"
        rm "$file"
    fi
done

# Temporary files
TEMP_FILES=(
    "cleanup_plan.txt"
    "api_service.log"
    "service.log"
    "worker_service.log"
)

for file in "${TEMP_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  🗑️  Removing $file"
        rm "$file"
    fi
done

echo ""
echo "Step 3: Consolidate documentation"
echo "─────────────────────────────────────────────────────────────────────"

# Create docs directory if it doesn't exist
mkdir -p docs

# Keep these essential docs in root
ESSENTIAL_DOCS=(
    "README.md"
    "SPLIT_SERVICES_ARCHITECTURE.md"
    "URL_NORMALIZATION_COMPLETE.md"
)

# Archive obsolete/duplicate docs
OBSOLETE_DOCS=(
    "2-SERVICE_ARCHITECTURE_GUIDE.md"
    "API_ENDPOINTS_AND_FLOWS.md"
    "ARCHITECTURE_FILE_GUIDE.md"
    "CHROME_EXTENSION_TEST_GUIDE.md"
    "COMPLETE_TESTING_GUIDE.md"
    "CORRECT_2_SERVICE_ARCHITECTURE.md"
    "IMPLEMENTATION_COMPLETE.md"
    "IMPLEMENTATION_STATUS_V3.md"
    "QUICKSTART_SPLIT_SERVICES.md"
    "QUICK_START.md"
    "REFACTORING_COMPLETE.md"
    "REFACTORING_TEST_SUCCESS.md"
)

mkdir -p "$ARCHIVE_DIR/docs"

for doc in "${OBSOLETE_DOCS[@]}"; do
    if [ -f "$doc" ]; then
        echo "  📦 Archiving $doc"
        mv "$doc" "$ARCHIVE_DIR/docs/"
    fi
done

echo ""
echo "Step 4: Clean up Chrome extension test files"
echo "─────────────────────────────────────────────────────────────────────"

# Remove duplicate/test manifest files
CHROME_TEST_FILES=(
    "chrome-extension/manifest-backup.json"
    "chrome-extension/manifest-debug.json"
    "chrome-extension/manifest-edge.json"
    "chrome-extension/manifest-minimal.json"
    "chrome-extension/manifest-ultra-minimal.json"
    "chrome-extension/manifest-v2.json"
    "chrome-extension/debug-edge.js"
    "chrome-extension/test-api.js"
    "chrome-extension/test-simple.js"
    "chrome-extension/question-injector.js"
    "chrome-extension/simple-question-injector.js"
)

for file in "${CHROME_TEST_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  🗑️  Removing $file"
        rm "$file"
    fi
done

echo ""
echo "Step 5: Remove Python cache files"
echo "─────────────────────────────────────────────────────────────────────"

find . -type d -name "__pycache__" -not -path "./venv/*" -not -path "./archive/*" | while read dir; do
    echo "  🗑️  Removing $dir"
    rm -rf "$dir"
done

find . -type f -name "*.pyc" -not -path "./venv/*" -not -path "./archive/*" | while read file; do
    rm "$file"
done

echo ""
echo "Step 6: Summary"
echo "─────────────────────────────────────────────────────────────────────"

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Final directory structure:"
echo ""
echo "Production Services:"
echo "  ✅ api_service/          - REST API (port 8005)"
echo "  ✅ worker_service/       - Background processor"
echo "  ✅ shared/               - Shared code"
echo ""
echo "Frontend:"
echo "  ✅ chrome-extension/     - Test harness"
echo "  ✅ ui-js/                - Production library"
echo ""
echo "Configuration:"
echo "  ✅ docker-compose.split-services.yml"
echo "  ✅ requirements.txt"
echo "  ✅ start_split_services.sh"
echo ""
echo "Documentation:"
echo "  ✅ README.md"
echo "  ✅ SPLIT_SERVICES_ARCHITECTURE.md"
echo "  ✅ URL_NORMALIZATION_COMPLETE.md"
echo ""
echo "Archived to: $ARCHIVE_DIR"
echo ""
echo "════════════════════════════════════════════════════════════════════"

