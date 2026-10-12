# 🎙️ Whisper Local — Extensão para Adobe Premiere Pro (macOS)

Extensão nativa (UXP) para o **Adobe Premiere Pro** que integra o **OpenAI Whisper** localmente para transcrição de áudio e geração automática de legendas `.srt` sincronizadas diretamente na sua timeline.

Sem custos de API, sem limite de minutos e 100% privado na sua máquina.

---

## ✨ Funcionalidades

- **100% Local e Gratuito:** Processamento executado na GPU/CPU do seu Mac usando o modelo Whisper local (suporte aos modelos `turbo`, `tiny`, `base`, `small`, `medium`, `large`).
- **Suporte a Múltiplos Clipes:** Selecione um ou vários clipes na Timeline ao mesmo tempo. As legendas são geradas e sincronizadas de uma só vez em um único arquivo `.srt`.
- **Respeita Pontos de Entrada e Saída (In/Out):** Transcreve apenas o trecho cortado na edição e calcula o offset para que o arquivo `.srt` caia exatamente na posição do clipe na sequência.
- **Formatação Inteligente de Texto (Português):**
  - Concatena palavras compostas com hífen (`entre-eixos` em vez de `entre -eixos`).
  - Corrige números decimais com vírgula ou ponto (`2,80` em vez de `2, 80`).
  - Corrige espaçamentos em porcentagens (`10%`).
  - Converte valores por extenso para moeda (`12 mil reais` → `R$ 12 mil`).
- **Quebra de Legendas Harmoniosa:** Agrupa o texto em blocos personalizáveis (padrão: 7 palavras com quebra na 4ª palavra), evitando frases extensas na tela.
- **Importação Automática:** O arquivo `.srt` é salvo na pasta do vídeo e automaticamente importado para a aba Projeto do Premiere.
- **Servidor em Segundo Plano Silencioso:** Opção de rodar como serviço do sistema no login sem precisar de terminais abertos.

---

## 📁 Estrutura do Projeto

```text
├── plugin/               # Código do painel UXP (HTML, CSS, JS, manifest)
│   ├── index.html        # Interface do painel
│   ├── index.js          # Lógica do painel e comunicação com o Premiere
│   └── manifest.json     # Manifesto UXP (Permissões de rede e sistema)
├── server/               # Servidor local e pipeline do Whisper
│   ├── server.py         # Servidor HTTP local (porta 17321)
│   ├── transcribe.py     # Script de corte FFmpeg, Whisper e formatação SRT
│   ├── start.command     # Iniciador manual do servidor via Terminal
│   └── install-autostart.sh # Inicia o servidor automaticamente no boot do macOS
├── setup.sh              # Script de instalação de dependências (FFmpeg + Whisper)
├── install-plugin.sh     # Empacota e instala o Whisper.ccx no Premiere
├── Whisper.ccx           # Pacote do plugin pronto para instalação no Creative Cloud
└── README.md
```

---

## 🛠️ Pré-requisitos

1. **macOS** (Apple Silicon M1/M2/M3/M4 ou Intel).
2. **Adobe Premiere Pro 25.6 ou superior** (com suporte à arquitetura UXP).
3. **Homebrew** instalado ([brew.sh](https://brew.sh)).

---

## 🚀 Instalação Rápida

### 1. Clonar o repositório
```bash
git clone https://github.com/SEU-USUARIO/whisper-premiere.git
cd whisper-premiere
```

### 2. Instalar dependências
Execute o script de configuração inicial para instalar o **FFmpeg** e o pacote **openai-whisper**:
```bash
chmod +x setup.sh install-plugin.sh server/*.sh server/*.command
./setup.sh
```

### 3. Configurar o Servidor Local
Você tem duas opções para rodar o servidor:

- **Opção A (Recomendada — Automática):**  
  Configure para iniciar sozinho ao ligar o Mac (em background, sem janelas abertas):
  ```bash
  server/install-autostart.sh
  ```
  *(Para desativar no futuro, basta rodar `server/install-autostart.sh remove`)*

- **Opção B (Manual):**  
  Dê dois cliques em `server/start.command` no Finder ou rode `python3 server/server.py` no terminal e mantenha a janela aberta enquanto edita.

### 4. Instalar o Plugin no Premiere Pro
- Basta dar **2 cliques no arquivo `Whisper.ccx`** no Finder e confirmar a instalação pelo **Adobe Creative Cloud**;  
  *OU*
- Rodar no Terminal:
  ```bash
  ./install-plugin.sh
  ```

---

## 🎬 Como Usar

1. Abra o **Adobe Premiere Pro**.
2. Abra o painel em: **Janela (Window) > Plugins > Whisper Local**.
3. O status exibirá a bolinha verde: **"Servidor conectado"**.
4. Selecione um ou mais clipes na sua **Timeline** (ou na janela Projeto).
5. Clique no botão **"Usar seleção"**.
6. Escolha o **Modelo** desejado (o `Turbo` oferece um equilíbrio excelente entre velocidade e precisão) e os parâmetros de quebra.
7. Clique em **"Transcrever"**.
8. Acompanhe a barra de progresso. Ao concluir, o arquivo `.srt` será criado junto à mídia de origem e adicionado aos itens do projeto.

---

## 🔍 Solução de Problemas

- **"Servidor offline" no painel:**
  - Verifique se o servidor está rodando. Se configurou o autostart, veja o log em `/tmp/whisper-server.log`.
  - Para iniciar manualmente a qualquer momento, execute `server/start.command`.
- **O Premiere não carrega o plugin ou não conecta ao UXP:**
  - No Premiere Pro, vá em **Ajustes (Preferences) > Plugins** e certifique-se de que a opção **"Enable developer mode"** está marcada se estiver testando diretamente pelo UXP Developer Tool.
- **Python alternativo / Conda / Venv:**
  - Caso seu ambiente Python com Whisper esteja em um caminho customizado, defina a variável antes de iniciar o servidor:
    ```bash
    export WHISPER_PYTHON="/caminho/do/seu/venv/bin/python3"
    ```

---

## 📄 Licença

Este projeto é disponibilizado sob a licença [MIT](LICENSE). Sinta-se livre para usar, modificar e contribuir!
