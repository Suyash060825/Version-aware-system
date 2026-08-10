#!/usr/bin/env bash
# ==============================================================================
# Model Pull and Pre-Warm Script for Ollama / Local LLM Backend
# ==============================================================================
set -euo pipefail

OLLAMA_URL="${OLLAMA_BASE_URL:-${OLLAMA_URL:-http://localhost:11434}}"
MODEL_NAME="${LOCAL_LLM_MODEL:-${OLLAMA_MODEL:-llama3.1:8b-instruct-q4_K_M}}"

echo "=========================================================="
echo "  Policy Ledger - Local Model Warmup Script"
echo "  Target URL   : ${OLLAMA_URL}"
echo "  Target Model : ${MODEL_NAME}"
echo "=========================================================="

# 1. Wait for Ollama service to respond
echo "[1/3] Checking Ollama server health at ${OLLAMA_URL}..."
MAX_ATTEMPTS=30
ATTEMPT=0

until curl -s -f "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; do
    ATTEMPT=$((ATTEMPT + 1))
    if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
        echo "[ERROR] Ollama service not reachable at ${OLLAMA_URL} after ${MAX_ATTEMPTS} attempts."
        exit 1
    fi
    echo "Waiting for Ollama service... (attempt ${ATTEMPT}/${MAX_ATTEMPTS})"
    sleep 2
done

echo "[OK] Ollama server is active."

# 2. Check if model is already pulled
echo "[2/3] Checking if model '${MODEL_NAME}' is available..."
TAGS_JSON=$(curl -s "${OLLAMA_URL}/api/tags")

if echo "${TAGS_JSON}" | grep -q "\"name\":\"${MODEL_NAME}"; then
    echo "[OK] Model '${MODEL_NAME}' is already downloaded."
else
    echo "[INFO] Pulling model '${MODEL_NAME}' via Ollama API..."
    PULL_RESPONSE=$(curl -s -X POST "${OLLAMA_URL}/api/pull" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"${MODEL_NAME}\", \"stream\": false}")

    if echo "${PULL_RESPONSE}" | grep -q '"status":"success"'; then
        echo "[OK] Successfully pulled '${MODEL_NAME}'."
    else
        echo "[WARN] Direct API pull output: ${PULL_RESPONSE}"
        echo "[INFO] Trying fallback pull command..."
        if command -v ollama > /dev/null 2>&1; then
            ollama pull "${MODEL_NAME}"
        fi
    fi
fi

# 3. Pre-warm model in memory with dummy inference
echo "[3/3] Pre-warming model '${MODEL_NAME}' in memory..."
WARMUP_RESP=$(curl -s -X POST "${OLLAMA_URL}/api/generate" \
    -H "Content-Type: application/json" \
    -d "{\"model\": \"${MODEL_NAME}\", \"prompt\": \"System check: respond OK.\", \"stream\": false}")

if echo "${WARMUP_RESP}" | grep -q '"response"'; then
    echo "[SUCCESS] Model '${MODEL_NAME}' is warmed up and ready for RAG inference."
    exit 0
else
    echo "[WARNING] Model pre-warm returned unexpected response: ${WARMUP_RESP}"
    # Return 0 so app can still boot, falling back gracefully if needed
    exit 0
fi
