#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Azure App Service Linux default deployment path is /home/site/wwwroot
# Determine running directory context
if [ -d "/home/site/wwwroot" ]; then
    DEPLOY_DIR="/home/site/wwwroot"
else
    DEPLOY_DIR="$PWD"
fi

# Fallback pathing logic for repository layout (root vs nested backend folder)
if [ -d "$DEPLOY_DIR/backend" ]; then
    TARGET_DIR="$DEPLOY_DIR/backend"
else
    TARGET_DIR="$DEPLOY_DIR"
fi

cd "$TARGET_DIR"
echo "=== Initializing Azure App Service Linux Startup Sequence ==="
echo "Working Directory: $TARGET_DIR"

# 1. Virtual Environment Activation (Azure Python images default path or local .venv)
if [ -d "/antenv" ]; then
    echo "Activating Azure default Python virtual environment..."
    source /antenv/bin/activate
elif [ -d ".venv" ]; then
    echo "Activating local Python virtual environment..."
    source .venv/bin/activate
else
    echo "Warning: No virtual environment isolated. Utilizing global context."
fi

# 2. Automated Pip Installation Dependency Sync Check
if [ -f "requirements.txt" ]; then
    echo "Verifying and updating environment dependencies via pip..."
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "Dependencies successfully updated."
else
    echo "Warning: requirements.txt not found. Skipping package sync."
fi

# 3. Knowledge Base PDF Extraction Safeguard
KB_PDF_DIR="data/kb_pdfs"
REQUIRED_PDFS=(
    "ADS-KB-ASSET-001.pdf"
    "ADS-KB-NET-002.pdf"
    "ADS-KB-IAM-003.pdf"
    "ADS-KB-M365-004.pdf"
    "ADS-KB-SEC-005.pdf"
)

GENERATE_NEEDED=false
mkdir -p "$KB_PDF_DIR"

for pdf in "${REQUIRED_PDFS[@]}"; do
    if [ ! -f "$KB_PDF_DIR/$pdf" ]; then
        echo "Missing file asset: $KB_PDF_DIR/$pdf"
        GENERATE_NEEDED=true
        break
    fi
done

if [ "$GENERATE_NEEDED" = true ]; then
    echo "Knowledge Base files missing or out of date. Initiating automated ReportLab generation script..."
    python -m scripts.generate_kb_pdfs
    echo "Knowledge Base PDFs generated successfully."
else
    echo "All Knowledge Base PDFs verified in '$KB_PDF_DIR'. Skipping regeneration."
fi

# 4. Ingest/Sync PDF metadata to Azure AI Search if needed in your CI/CD pipeline
# Un-comment the line below if you want automated re-indexing on every cold boot:
# python -m app.rag.ingest

# 5. Launch Production Server
# Note: Removed --reload flag as it causes instability in enterprise Azure environments.
# Uses 'exec' so the process takes over PID 1, allowing Azure to route shutdown/restart signals cleanly.
echo "Launching FastAPI backend application on port 8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
