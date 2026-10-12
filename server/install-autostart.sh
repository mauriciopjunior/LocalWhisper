#!/bin/bash
# Faz o servidor iniciar sozinho ao fazer login no macOS (e reiniciar se cair).
# Para remover: ./install-autostart.sh remove
LABEL="com.local.whisper.server"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
DIR="$(cd "$(dirname "$0")" && pwd)"

if [ "$1" = "remove" ]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "Servidor em background removido com sucesso."
  exit 0
fi

PYTHON_BIN="$(PATH=/opt/homebrew/bin:/usr/local/bin:$PATH command -v python3)"
[ -z "$PYTHON_BIN" ] && { echo "Erro: python3 não encontrado. Execute ./setup.sh primeiro."; exit 1; }

mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>$PYTHON_BIN</string><string>$DIR/server.py</string></array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/tmp/whisper-server.log</string>
  <key>StandardErrorPath</key><string>/tmp/whisper-server.log</string>
</dict></plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "Servidor configurado para iniciar automaticamente no login!"
echo "Logs de execução: /tmp/whisper-server.log"
