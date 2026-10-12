#!/bin/bash
# Instala ffmpeg e openai-whisper (Python). Uso: ./setup.sh
set -e
command -v brew >/dev/null || { echo "Instale o Homebrew primeiro: https://brew.sh"; exit 1; }
brew install ffmpeg
PY="$(command -v python3)"
"$PY" -m pip install --upgrade openai-whisper || "$PY" -m pip install --break-system-packages --upgrade openai-whisper
echo "Configuração concluída com sucesso!"
echo "(O modelo 'turbo' é baixado automaticamente no primeiro uso)."
echo "Caso use um ambiente virtual ou outro Python, defina WHISPER_PYTHON=/caminho/do/python antes de iniciar o servidor."
