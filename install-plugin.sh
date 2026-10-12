#!/bin/bash
# Empacota o plugin em Whisper.ccx e instala no Premiere Pro
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
UPIA="/Library/Application Support/Adobe/Adobe Desktop Common/RemoteComponents/UPI/UnifiedPluginInstallerAgent/UnifiedPluginInstallerAgent.app/Contents/macOS/UnifiedPluginInstallerAgent"

echo "1. Gerando pacote Whisper.ccx atualizado..."
rm -f "$DIR/Whisper.ccx"
(cd "$DIR/plugin" && zip -q -r "$DIR/Whisper.ccx" . -x "*.DS_Store")

echo "2. Instalando Whisper.ccx..."
if pgrep -x "Creative Cloud" >/dev/null && [ -f "$UPIA" ]; then
  "$UPIA" --install "$DIR/Whisper.ccx" || open "$DIR/Whisper.ccx"
else
  open "$DIR/Whisper.ccx"
fi

echo "Concluído! Confirme a instalação na janela do Creative Cloud, se solicitado."
