import os
import re
import random
import urllib.request
import urllib.parse
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
# Habilita CORS para aceitar pedidos do seu GitHub Pages
CORS(app)

# ============================================================
#  1. Provedor de imagem
# ============================================================
# "pollinations"  -> GRÁTIS, sem chave, sem limites práticos (padrão)
# "openrouter"    -> usa sua chave OPENROUTER_API_KEY (créditos)
PROVIDER = os.getenv("IMAGE_PROVIDER", "pollinations")

# Chave do OpenRouter (só usada se PROVIDER=openrouter)
api_key = os.getenv("OPENROUTER_API_KEY")

# Modelo de imagem no OpenRouter (o antigo flux-1-schnell saiu do catálogo)
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "google/gemini-3.1-flash-lite-image")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "8000"))

client = None
if api_key:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


# ============================================================
#  2. ENRIQUECEDOR DE PROMPT — transforma o pedido do usuário
#     em uma descrição esteticamente superior para a IA
# ============================================================

# Termos de qualidade (em inglês — modelos de imagem respondem melhor)
QUALIDADE_BASE = (
    "ultra high resolution, sharp focus, intricate details, "
    "professional color grading, award-winning composition"
)

# Estilos detectados automaticamente por palavras-chave do usuário
ESTILOS = [
    # (palavras-chave, sufixo de estilo)
    (["foto", "photo", "realista", "fotografic", "photographic", "retrato"],
     "photorealistic, professional photography, 85mm lens, shallow depth of field, "
     "natural golden-hour lighting, film grain"),
    (["cartoon", "desenho", "anime", "animac", "animation"],
     "vibrant cartoon style, smooth cel shading, expressive characters, "
     "polished animation still, bold outlines"),
    (["pixel", "8-bit", "8bit", "retro", "games retro"],
     "crisp pixel art, meticulous pixel detail, retro 16-bit game aesthetic, "
     "limited vibrant palette"),
    (["pintura", "painting", "oleo", "aquarela", "watercolor", "arte clas"],
     "fine art painting, rich visible brushstrokes, masterful chiaroscuro, "
     "museum-quality artwork"),
    (["futurista", "cyberpunk", "futuristic", "scifi", "space", "espaco", "galaxia", "galaxy"],
     "epic cinematic sci-fi concept art, volumetric lighting, glowing neon accents, "
     "dramatic atmosphere, deep space background"),
    (["natureza", "nature", "paisagem", "landscape", "montanha", "floresta", "praia"],
     "breathtaking landscape photography, golden hour light, god rays, "
     "ultra-detailed scenery, atmospheric depth"),
    (["minimal", "minimalista", "simples", "flat"],
     "elegant minimalism, clean geometric shapes, soft studio lighting, "
     "balanced negative space, premium flat design"),
]

def enriquecer_prompt(prompt_usuario):
    """
    Melhora o prompt do usuário adicionando direção de estilo e termos
    de qualidade, para gerar imagens significativamente mais bonitas.
    """
    base = (prompt_usuario or "").strip()
    if not base:
        base = "uma cena surreal e vibrante, cheia de detalhes"

    texto = base.lower()

    # 1. Detecta o estilo mais provável pelas palavras do usuário
    estilo_escolhido = None
    for palavras, sufixo in ESTILOS:
        if any(p in texto for p in palavras):
            estilo_escolhido = sufixo
            break

    if not estilo_escolhido:
        estilo_escolhido = (
            "stunning digital art, masterpiece quality, dramatic cinematic lighting, "
            "vibrant colors, dynamic composition"
        )

    # 2. Monta o prompt final (base + estilo + qualidade)
    prompt_final = f"{base}, {estilo_escolhido}, {QUALIDADE_BASE}"
    print(f"--- Prompt enriquecido: {prompt_final}")
    return prompt_final


def gerar_pollinations(prompt):
    """Geração de imagem GRÁTIS via Pollinations.ai (sem chave), com prompt enriquecido."""
    prompt_final = enriquecer_prompt(prompt)

    url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt_final)
    # 1024px para alta qualidade + enhance da própria Pollinations + modelo flux
    # seed aleatório para cada geração (variedade)
    url += ("?width=1024&height=1024&nologo=true&enhance=true&model=flux"
            f"&seed={random.randint(0, 99999)}")

    # Faz uma requisição HEAD/GET leve só para validar e devolve a URL
    # (o navegador do usuário baixa a imagem direto do Pollinations)
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status == 200:
                return url
    except Exception as e:
        print(f"Pollinations HEAD falhou: {e}")
    return url  # mesmo sem HEAD, a URL costuma funcionar


def extrair_url_imagem(completion):
    """Extrai a URL da imagem gerada pelo OpenRouter (formato Gemini/GPT Image)."""
    try:
        msg = completion.choices[0].message

        conteudo = getattr(msg, 'content', None)
        if isinstance(conteudo, list):
            partes = []
            for parte in conteudo:
                if isinstance(parte, dict):
                    if parte.get('type') == 'image_url':
                        url = parte.get('image_url', {}).get('url', '')
                        if url:
                            return url
                    partes.append(str(parte.get('text', '')))
                else:
                    partes.append(str(parte))
            conteudo = ' '.join(partes)

        if isinstance(conteudo, str):
            m = re.search(r'!\[[^\]]*\]\((https?://[^\s)]+)\)', conteudo)
            if m:
                return m.group(1).rstrip(')')
            m = re.search(r'(https?://[^\s)]+)', conteudo)
            if m:
                return m.group(1).rstrip(')')

        imagens = getattr(msg, 'images', None)
        if imagens:
            primeira = imagens[0]
            if isinstance(primeira, dict):
                if primeira.get('url'):
                    return primeira['url']
                if primeira.get('b64_json'):
                    return 'data:image/png;base64,' + primeira['b64_json']
            elif isinstance(primeira, str) and primeira.startswith('http'):
                return primeira

    except Exception as e:
        print(f"Erro ao extrair imagem: {e}")
    return None


@app.route('/gerar', methods=['POST'])
def gerar_imagem():
    dados = request.json
    prompt_usuario = dados.get('prompt') if dados else None

    if not prompt_usuario:
        return jsonify({"erro": "O prompt é obrigatório!"}), 400

    print(f"--- Recebido pedido: {prompt_usuario} ---")

    # ---- Provedor 1: Pollinations (grátis, padrão) ----
    if PROVIDER == "pollinations":
        try:
            url = gerar_pollinations(prompt_usuario)
            return jsonify({"url": url, "provider": "pollinations"})
        except Exception as e:
            print(f"Erro no Pollinations: {e}")
            return jsonify({"erro": str(e)}), 500

    # ---- Provedor 2: OpenRouter (requer chave/créditos) ----
    if client is None:
        return jsonify({"erro": "Servidor sem chave de API configurada. Contate o administrador."}), 500

    try:
        completion = client.chat.completions.create(
            model=IMAGE_MODEL,
            messages=[{"role": "user", "content": prompt_usuario}],
            modalities=["image", "text"],
            max_tokens=MAX_TOKENS,
        )
        url_imagem = extrair_url_imagem(completion)
        if url_imagem:
            return jsonify({"url": url_imagem, "provider": "openrouter"})
        else:
            return jsonify({"erro": "A IA não retornou uma imagem válida.",
                            "detalhes": str(getattr(completion.choices[0].message, 'content', ''))}), 500
    except Exception as e:
        print(f"Erro no servidor: {e}")
        return jsonify({"erro": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Rota de verificação (a Render usa para saber se o serviço está vivo)."""
    return jsonify({
        "status": "ok",
        "provider": PROVIDER,
        "api_key_configured": client is not None,
        "model": IMAGE_MODEL if PROVIDER == "openrouter" else "pollinations.ai (grátis)"
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
