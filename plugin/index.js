const ppro = require('premierepro');
const SERVER = 'http://127.0.0.1:17321';
const $ = (id) => document.getElementById(id);
async function getStartCommandPath() {
  try {
    const fs = require('uxp').storage.localFileSystem;
    const folder = await fs.getPluginFolder();
    if (folder && folder.nativePath) {
      const candidate = folder.nativePath.replace(/[\/\\]plugin[\/\\]?$/, '/server/start.command');
      if (candidate !== folder.nativePath) return candidate;
    }
  } catch (e) {}
  return localStorage.getItem('whisper_start_cmd') || 'server/start.command';
}

function setStatus(msg, cls) { const s = $('status'); s.textContent = msg; s.className = cls || ''; }
function setProgress(p) { $('fill').style.width = p + '%'; }

async function checkServer() {
  try {
    const h = await (await fetch(SERVER + '/health')).json();
    $('dot').className = 'dot on';
    $('btnStart').style.display = 'none';
    const missing = [!h.ffmpeg && 'ffmpeg', !h.python && 'python com openai-whisper'].filter(Boolean);
    $('srvText').textContent = missing.length ? 'Faltando: ' + missing.join(', ') : 'Servidor conectado';
    return true;
  } catch (e) {
    $('dot').className = 'dot off';
    $('btnStart').style.display = '';
    $('srvText').textContent = 'Servidor offline: ' + (e && e.message ? e.message : e);
    return false;
  }
}

$('btnStart').addEventListener('click', async () => {
  try {
    const { shell } = require('uxp');
    const cmd = await getStartCommandPath();
    await shell.openPath(cmd, 'Iniciar o servidor local do Whisper');
    $('srvText').textContent = 'Iniciando servidor…';
    for (let i = 0; i < 20; i++) {
      await new Promise(r => setTimeout(r, 1000));
      if (await checkServer()) return;
    }
    setStatus('Servidor não respondeu. Veja a janela do Terminal.', 'err');
  } catch (e) {
    setStatus('Inicie o servidor via terminal: server/start.command ou server/install-autostart.sh', 'err');
  }
});

// Obtém todos os clipes selecionados (timeline ou painel Projeto) com pontos de entrada/saída (s).
// Na timeline, "offset" = posição do clipe na sequência, para o SRT já sair alinhado.
async function getSelections() {
  const project = await ppro.Project.getActiveProject();
  if (!project) throw new Error('Nenhum projeto aberto');
  const secs = async (v) => { try { const t = await v; return t && typeof t.seconds === 'number' ? t.seconds : null; } catch (e) { return null; } };
  const out = [];
  const add = (c) => {
    if (!c.path) return;
    // Evita duplicar (ex.: vídeo + áudio vinculados do mesmo clipe)
    if (out.some(o => o.path === c.path && o.start === c.start && o.end === c.end && o.offset === c.offset)) return;
    out.push(c);
  };
  const range = (s, e) => (s !== null && e !== null && e > s) ? [s, e] : [null, null];

  try {
    const seq = await project.getActiveSequence();
    const sel = seq && await seq.getSelection();
    const tis = (sel && await sel.getTrackItems()) || [];
    for (const ti of tis) {
      try {
        const item = await ti.getProjectItem();
        const clip = ppro.ClipProjectItem.cast(item);
        const path = clip && await clip.getMediaFilePath();
        const [start, end] = range(await secs(ti.getInPoint()), await secs(ti.getOutPoint()));
        add({ path, start, end, offset: await secs(ti.getStartTime()) });
      } catch (e) { /* item sem mídia (gráfico, etc.) */ }
    }
  } catch (e) { /* ignora, tenta o painel Projeto */ }

  if (!out.length) {
    const sel = await ppro.ProjectUtils.getSelection(project);
    const items = (sel && await sel.getItems()) || [];
    for (const item of items) {
      try {
        const clip = ppro.ClipProjectItem.cast(item);
        const path = clip && await clip.getMediaFilePath();
        let start = null, end = null;
        try {
          const mt = ppro.Constants && ppro.Constants.MediaType ? ppro.Constants.MediaType.ANY : undefined;
          [start, end] = range(await secs(clip.getInPoint(mt)), await secs(clip.getOutPoint(mt)));
        } catch (e) { /* sem I/O */ }
        add({ path, start, end, offset: null }); // offset null = encadeia uma após a outra
      } catch (e) { /* bin/sequência: ignora */ }
    }
  }
  if (!out.length) throw new Error('Selecione clipes na timeline ou no painel Projeto');
  if (out.every(c => c.offset !== null)) out.sort((a, b) => a.offset - b.offset);
  return out;
}
let lastSels = null, lastLabel = '';

function label(sels) {
  return sels.length === 1 ? sels[0].path : sels.length + ' clipes selecionados';
}
function describe(sels) {
  const r = sels.filter(c => c.start !== null).length;
  return sels.length + ' clipe(s); ' + (r ? r + ' com entrada/saída' : 'mídia inteira');
}

$('btnSel').addEventListener('click', async () => {
  try {
    lastSels = await getSelections();
    lastLabel = label(lastSels);
    $('media').value = lastLabel;
    setStatus(describe(lastSels));
  } catch (e) { setStatus(e.message, 'err'); }
});

$('btnGo').addEventListener('click', async () => {
  const btn = $('btnGo');
  try {
    if (!(await checkServer())) throw new Error('Servidor offline');
    const typed = $('media').value.trim();
    let sels;
    if (typed && lastSels && typed === lastLabel) sels = lastSels;
    else if (typed) sels = [{ path: typed, start: null, end: null, offset: null }];
    else sels = await getSelections();
    lastSels = sels; lastLabel = label(sels);
    $('media').value = lastLabel;
    const useRange = $('useRange').checked;
    const clips = sels.map(c => ({
      path: c.path,
      start: useRange ? c.start : null, end: useRange ? c.end : null,
      offset: c.offset,
    }));
    btn.disabled = true; setProgress(0); setStatus('Enviando… ' + describe(sels));
    const r = await fetch(SERVER + '/transcribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        clips, model: $('model').value.toLowerCase(), language: $('lang').value.trim() || 'Portuguese',
        maxWords: parseInt($('maxWords').value, 10) || 7, breakAt: parseInt($('breakAt').value, 10) || 4,
      }),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || 'Erro no servidor');
    const srt = await poll(j.id);
    setProgress(100); setStatus('Pronto: ' + srt, 'ok');
    if ($('import').checked) await importSrt(srt);
  } catch (e) {
    setStatus(e.message, 'err');
  } finally { btn.disabled = false; }
});

async function poll(id) {
  for (;;) {
    await new Promise(r => setTimeout(r, 1000));
    const j = await (await fetch(SERVER + '/job/' + id)).json();
    setProgress(j.progress || 0);
    setStatus(j.status === 'transcribing' ? 'Transcrevendo… ' + (j.progress || 0) + '%' : 'Carregando modelo…');
    if (j.status === 'done') return j.srtPath;
    if (j.status === 'error') throw new Error(j.error);
  }
}

async function importSrt(srtPath) {
  try {
    const project = await ppro.Project.getActiveProject();
    const root = await project.getRootItem();
    await project.importFiles([srtPath], true, root, false);
    setStatus('SRT importado no projeto: ' + srtPath, 'ok');
  } catch (e) {
    setStatus('SRT salvo, mas importação falhou: ' + e.message, 'err');
  }
}

checkServer();
