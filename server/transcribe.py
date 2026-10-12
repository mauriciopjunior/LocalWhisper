import ssl
import whisper
import sys
import os
import re
import json
import argparse
import subprocess
import tempfile
from whisper.utils import get_writer

# Ignorar erro de certificado SSL
ssl._create_default_https_context = ssl._create_unverified_context

def limpar_e_formatar_texto(texto):
    """Aplica correções de espaçamento, hífens, decimais, porcentagem e formatação de moeda."""
    # 1. Corrige hífens separados por espaços (ex: "homem -aranha" -> "homem-aranha")
    texto = re.sub(r"\s*-\s*", "-", texto)
    
    # 2. Corrige separadores de números decimais (ex: "12 .3" -> "12.3", "2, 80" -> "2,80")
    texto = re.sub(r"(\d+)\s*([.,])\s*(\d+)", r"\1\2\3", texto)
    
    # 3. Corrige o símbolo de porcentagem colando-o no número (ex: "10 %" -> "10%")
    texto = re.sub(r"(\d+)\s+%", r"\1%", texto)
    
    # 4. Converte "X mil reais" para "R$ X mil" (ex: "12 mil reais" -> "R$ 12 mil")
    texto = re.sub(r"(\d+)\s*(mil|milhão|milhões|bilhão|bilhões)?\s*reais", r"R$ \1 \2", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\s+$", "", texto) 
    
    return texto

def merge_words(words):
    """Une palavras que o Whisper separou indevidamente (ex: 'entre' + '-eixos', '2,' + '80'),
    para que nunca sejam divididas entre linhas ou legendas."""
    merged = []
    for w in words:
        t = w["word"].strip()
        if merged:
            prev = merged[-1]
            p = prev["word"].strip()
            glue = (
                t.startswith("-") or p.endswith("-")
                or (re.search(r"\d[.,]$", p) and re.match(r"\d", t))
                or (re.search(r"\d$", p) and re.match(r"[.,]\d", t))
            )
            if glue:
                prev["word"] = p + t
                prev["end"] = w["end"]
                continue
        merged.append({"word": t, "start": w["start"], "end": w["end"]})
    return merged

def group_by_words(result, max_words=7, break_at=4):
    """Agrupa em 7 palavras e insere quebra de linha na 4ª palavra."""
    new_segments = []
    all_words = []
    for segment in result["segments"]:
        all_words.extend(segment.get("words", []))
    all_words = merge_words(all_words)
    
    for i in range(0, len(all_words), max_words):
        chunk = all_words[i : i + max_words]
        if not chunk:
            continue
            
        words_text = [w["word"].strip() for w in chunk]
        
        if len(words_text) > break_at:
            line1 = " ".join(words_text[:break_at])
            line2 = " ".join(words_text[break_at:])
            final_text = f"{line1}\n{line2}"
        else:
            final_text = " ".join(words_text)
            
        final_text = limpar_e_formatar_texto(final_text)
            
        new_segments.append({
            "id": len(new_segments),
            "start": chunk[0]["start"],
            "end": chunk[-1]["end"],
            "text": final_text
        })
    
    result["segments"] = new_segments
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", required=True, help="JSON: [{path,start,end,offset}]")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--out-name", required=True)
    ap.add_argument("--model", default="turbo")
    ap.add_argument("--language", default="Portuguese")
    ap.add_argument("--max-words", type=int, default=7)
    ap.add_argument("--break-at", type=int, default=4)
    a = ap.parse_args()
    clips = json.loads(a.clips)

    print(f"Carregando IA (Modelo {a.model})...", flush=True)
    model = whisper.load_model(a.model)

    all_segments = []
    running = 0.0  # posição encadeada para clipes sem offset (seleção do painel Projeto)
    for idx, c in enumerate(clips):
        print(f"@@CLIP {idx} {len(clips)}", flush=True)
        file_path = c["path"]
        start, end = c.get("start"), c.get("end")
        audio_path, tmp = file_path, None
        if start is not None and end is not None and end > start:
            # Recorta apenas o trecho entre entrada e saída
            tmp = os.path.join(tempfile.gettempdir(), f"whisper-range-{os.getpid()}-{idx}.wav")
            subprocess.run(["ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", file_path,
                            "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", tmp],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            audio_path = tmp
            duration = end - start
        else:
            duration = len(whisper.load_audio(file_path)) / 16000.0

        print(f"Gerando legendas ({a.max_words} palavras): {os.path.basename(file_path)}", flush=True)
        # verbose=False habilita a barra de progresso (tqdm) lida pelo servidor
        result = model.transcribe(audio_path, language=a.language, word_timestamps=True, verbose=False)
        result = group_by_words(result, max_words=a.max_words, break_at=a.break_at)

        offset = c.get("offset")
        if offset is None:
            offset = running
        running = offset + duration
        for seg in result["segments"]:
            seg["start"] += offset
            seg["end"] += offset
            all_segments.append(seg)
        if tmp and os.path.exists(tmp):
            os.remove(tmp)

    all_segments.sort(key=lambda s: s["start"])
    for i, seg in enumerate(all_segments):
        seg["id"] = i

    writer = get_writer("srt", a.out_dir)
    writer({"segments": all_segments, "text": ""}, os.path.join(a.out_dir, a.out_name + ".wav"),
           {"max_line_width": None, "max_line_count": None, "highlight_words": False})

    print("\nConcluído.", flush=True)

if __name__ == "__main__":
    main()
