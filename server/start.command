#!/bin/bash
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
python3 server.py
echo
echo "O servidor foi encerrado. Pressione Enter para fechar."
read
