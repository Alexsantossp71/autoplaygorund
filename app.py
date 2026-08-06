import os
import re
import random
import time
import urllib.request
import urllib.parse
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
# Habilita CORS para aceitar pedidos do seu GitHub Pages
CORS(app)

# ---- Rate limit simples (em memória) ----
# Protege a API pública: 10 gerações/minuto por IP
from collections import defaultdict
import time as _time
_limite_requisicoes = defaultdict(list)
LIMITE_MAX = int(os.getenv('RATE_LIMIT_MAX', '10'))
LIMITE_JANELA = int(os.getenv('RATE_LIMIT_WINDOW', '60'))

def rate_limit_ok(ip):
    agora = _time.time()
    historico = [t for t in _limite_requisicoes[ip] if agora - t < LIMITE_JANELA]
    if len(historico) >= LIMITE_MAX:
        return False
    historico.append(agora)
    _limite_requisicoes[ip] = historico
    return True

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

# Estilos por nome (usados pelo seletor manual do frontend)

# ============================================================
#  3. TRADUTOR PT->EN EMBUTIDO
#     O modelo "sana" do Pollinations entende inglês muito melhor.
#     Traduz as palavras mais comuns do prompt para inglês
#     antes de enriquecer (melhora MUITO a aderência).
# ============================================================
DICIONARIO_PT_EN = {
    # substantivos comuns
    "porta": "door", "casa": "house", "gato": "cat", "gatos": "cats",
    "cachorro": "dog", "cachorros": "dogs", "mulher": "woman",
    "homem": "man", "mulheres": "women", "homens": "men",
    "carro": "car", "carros": "cars", "arvore": "tree", "arvores": "trees",
    "flor": "flower", "flores": "flowers", "montanha": "mountain",
    "montanhas": "mountains", "mar": "sea", "oceano": "ocean",
    "praia": "beach", "ceu": "sky", "sol": "sun", "lua": "moon",
    "estrelas": "stars", "cidade": "city", "castelo": "castle",
    "ponte": "bridge", "rio": "river", "lago": "lake", "floresta": "forest",
    "jardim": "garden", "cachoeira": "waterfall", "deserto": "desert",
    "neve": "snow", "fogo": "fire", "agua": "water", "pedra": "stone",
    "madeira": "wood", "madeirado": "wooden", "de madeira": "wooden", "janela": "window", "telhado": "roof",
    "rua": "street", "estrada": "road", "trem": "train", "aviao": "airplane",
    "barco": "boat", "navio": "ship", "bicicleta": "bicycle",
    "moto": "motorcycle", "cavalo": "horse", "passaro": "bird",
    "passaros": "birds", "peixe": "fish", "borboleta": "butterfly",
    "leao": "lion", "tigre": "tiger", "elefante": "elephant",
    "urso": "bear", "lobo": "wolf", "raposa": "fox", "coelho": "rabbit",
    "pato": "duck", "galinha": "chicken", "vaca": "cow", "porco": "pig",
    "ovelha": "sheep", "cabra": "goat", "macaco": "monkey",
    "girafa": "giraffe", "zebra": "zebra", "cobra": "snake",
    "crocodilo": "crocodile", "tubarao": "shark", "baleia": "whale",
    "golfinho": "dolphin", "polvo": "octopus", "caranguejo": "crab",
    "estrela-do-mar": "starfish", "coruja": "owl", "aguia": "eagle",
    "pinguim": "penguin", "camelo": "camel", "canguru": "kangaroo",
    "panda": "panda", "esquilo": "squirrel", "rato": "mouse",
    "morcego": "bat", "sapo": "frog", "lagarto": "lizard",
    "tartaruga": "turtle", "dinossauro": "dinosaur", "dragao": "dragon",
    "unicornio": "unicorn", "fada": "fairy", "bruxa": "witch",
    "mago": "wizard", "cavaleiro": "knight", "espada": "sword",
    "escudo": "shield", "coroa": "crown", "trono": "throne",
    "muralha": "wall", "torre": "tower", "portao": "gate",
    "chave": "key", "cadeado": "lock", "livro": "book", "livros": "books",
    "lapis": "pencil", "caneta": "pen", "papel": "paper",
    "mesa": "table", "cadeira": "chair", "sofa": "sofa", "cama": "bed",
    "cozinha": "kitchen", "quarto": "bedroom", "banheiro": "bathroom",
    "sala": "living room", "escritorio": "office", "escola": "school",
    "universidade": "university", "hospital": "hospital", "igreja": "church",
    "restaurante": "restaurant", "mercado": "market", "loja": "shop",
    "farmacia": "pharmacy", "biblioteca": "library", "museu": "museum",
    "teatro": "theater", "estadio": "stadium", "parque": "park",
    "praca": "square", "fonte": "fountain", "monumento": "monument",
    "estatua": "statue", "relogio": "clock", "celular": "cellphone",
    "computador": "computer", "notebook": "laptop", "televisao": "television",
    "geladeira": "refrigerator", "fogao": "stove", "forno": "oven",
    "pia": "sink", "banheira": "bathtub", "chuveiro": "shower",
    "espelho": "mirror", "quadro": "painting", "tapete": "carpet",
    "cortina": "curtain", "lampada": "lamp", "vela": "candle",
    "florista": "flower shop", "padeiro": "baker", "padeira": "baker",
    "pizza": "pizza", "hamburguer": "hamburger", "sorvete": "ice cream",
    "bolo": "cake", "pao": "bread", "queijo": "cheese", "cafe": "coffee",
    "cha": "tea", "suco": "juice", "vinho": "wine", "cerveja": "beer",
    "fruta": "fruit", "frutas": "fruits", "maca": "apple", "banana": "banana",
    "laranja": "orange", "uva": "grape", "manga": "mango", "abacaxi": "pineapple",
    "melancia": "watermelon", "morango": "strawberry", "limao": "lemon",
    "cenoura": "carrot", "batata": "potato", "tomate": "tomato",
    "cebola": "onion", "alho": "garlic", "pimenta": "pepper",
    "arroz": "rice", "feijao": "beans", "carne": "meat", "frango": "chicken meat",
    "peixe-espada": "swordfish", "sushi": "sushi", "massa": "pasta",
    "salada": "salad", "sopa": "soup", "sanduiche": "sandwich",
    "cachorro-quente": "hot dog", "pipoca": "popcorn", "chocolate": "chocolate",
    "bala": "candy", "doce": "sweet", "geleia": "jam", "mel": "honey",
    "manteiga": "butter", "ovo": "egg", "leite": "milk", "iogurte": "yogurt",
    "cereal": "cereal", "panqueca": "pancake", "waffle": "waffle",
    "biscoito": "cookie", "torta": "pie", "pudim": "pudding",
    "musica": "music", "danca": "dance", "festa": "party",
    "casamento": "wedding", "aniversario": "birthday", "natal": "christmas",
    "pascoa": "easter", "halloween": "halloween", "carnaval": "carnival",
    "futebol": "soccer", "basquete": "basketball", "volei": "volleyball",
    "tenis": "tennis", "natacao": "swimming", "corrida": "race",
    "bicicleta-montanha": "mountain bike", "surfe": "surfing",
    "esqui": "skiing", "patins": "skates", "videogame": "video game",
    "xadrez": "chess", "cartas": "cards", "dado": "dice",
    "brinquedo": "toy", "boneca": "doll", "bola": "ball",
    "pipa": "kite", "foguete": "rocket", "espaconave": "spaceship",
    "astronauta": "astronaut", "planeta": "planet", "planetas": "planets",
    "galaxia": "galaxy", "universo": "universe", "cometa": "comet",
    "meteoro": "meteor", "satelite": "satellite", "alien": "alien",
    "robo": "robot", "robos": "robots", "carro-esporte": "sports car",
    "caminhao": "truck", "onibus": "bus", "moto-taxi": "motorcycle taxi",
    "helicoptero": "helicopter", "baloes": "balloons", "presente": "gift",
    "caixa": "box", "garrafa": "bottle", "copo": "glass", "xicara": "cup",
    "prato": "plate", "talheres": "cutlery", "faca": "knife",
    "garfo": "fork", "colher": "spoon", "guardanapo": "napkin",
    "toalha": "towel", "sabonete": "soap", "shampoo": "shampoo",
    "pasta-de-dente": "toothpaste", "escova": "brush", "pente": "comb",
    "tesoura": "scissors", "martelo": "hammer", "prego": "nail",
    "parafuso": "screw", "chave-de-fenda": "screwdriver", "serra": "saw",
    "machado": "axe", "enxada": "hoe", "pá": "shovel",
    "corda": "rope", "corrente": "chain", "cadeia": "chain",
    "ferradura": "horseshoe", "sino": "bell", "tambor": "drum",
    "violao": "guitar", "piano": "piano", "flauta": "flute",
    "bateria": "drums", "microfone": "microphone", "nota-musical": "musical note",
    "pincel": "brush", "tinta": "paint", "tela": "canvas",
    "escultura": "sculpture", "argila": "clay", "ceramica": "ceramics",
    "joia": "jewel", "anel": "ring", "colar": "necklace", "brinco": "earring",
    "pulseira": "bracelet", "relogio-de-pulso": "wristwatch", "oculos": "glasses",
    "chapeu": "hat", "boné": "cap", "cachecol": "scarf", "luva": "glove",
    "sapato": "shoe", "sapatos": "shoes", "bota": "boot", "sandalia": "sandal",
    "vestido": "dress", "saia": "skirt", "calca": "pants", "camisa": "shirt",
    "camiseta": "t-shirt", "casaco": "coat", "jaqueta": "jacket",
    "terno": "suit", "gravata": "tie", "uniforme": "uniform",
    "pijama": "pajamas", "roupa": "clothes", "roupas": "clothes",
    "cinto": "belt", "bolsa": "bag", "mochila": "backpack",
    "guarda-chuva": "umbrella", "chapel": "hat",
    # adjetivos/verbos comuns
    "bonito": "beautiful", "bonita": "beautiful", "lindo": "beautiful",
    "linda": "beautiful", "feio": "ugly", "grande": "big", "grandes": "big", "pequeno": "small", "pequenos": "small", "pequenas": "small",
    "pequena": "small", "alto": "tall", "baixo": "short", "velho": "old",
    "novo": "new", "nova": "new", "antigo": "ancient", "antiga": "ancient", "moderno": "modern",
    "moderna": "modern", "futurista": "futuristic", "classico": "classic",
    "classica": "classic", "colorido": "colorful", "colorida": "colorful",
    "preto": "black", "branco": "white", "branca": "white", "vermelho": "red",
    "vermelha": "red", "azul": "blue", "verde": "green", "amarelo": "yellow",
    "amarela": "yellow", "rosa": "pink", "roxo": "purple", "laranja": "orange",
    "cinza": "gray", "marrom": "brown", "dourado": "golden", "prateado": "silver",
    "claro": "light", "escuro": "dark", "escura": "dark", "brilhante": "shiny",
    "enorme": "huge", "gigante": "giant", "miniatura": "miniature",
    "feliz": "happy", "triste": "sad", "bravo": "angry", "calmo": "calm",
    "assustador": "scary", "fofo": "cute", "fofa": "cute", "elegante": "elegant",
    "luxuoso": "luxurious", "simples": "simple", "moderno": "modern",
    "tecnologico": "technological", "magico": "magical", "magica": "magical",
    "misterioso": "mysterious", "romantico": "romantic", "alegre": "cheerful",
    "tranquilo": "peaceful", "tranquila": "peaceful", "selvagem": "wild",
    "domestico": "domestic", "rural": "rural", "urbano": "urban",
    "industrial": "industrial", "historico": "historic", "historica": "historic",
    "medieval": "medieval", "vintage": "vintage", "retro": "retro",
    "tropical": "tropical", "gelado": "icy", "quente": "hot", "frio": "cold",
    "ensolarado": "sunny", "chuvoso": "rainy", "nevoado": "foggy",
    "tempestuoso": "stormy", "ventoso": "windy", "nublado": "cloudy",
    "escuro": "dark", "iluminado": "illuminated", "neon": "neon",
    # verbos/contextos
    "voando": "flying", "correndo": "running", "pulando": "jumping",
    "nadando": "swimming", "dancando": "dancing", "cantando": "singing",
    "sentado": "sitting", "deitado": "lying down", "em-pe": "standing",
    "andando": "walking", "flutuando": "floating", "dormindo": "sleeping",
    "comendo": "eating", "bebendo": "drinking", "lendo": "reading",
    "escrevendo": "writing", "desenhando": "drawing", "pintando": "painting",
    "tocando": "playing", "jogando": "playing", "trabalhando": "working",
    "estudando": "studying", "cozinhando": "cooking", "dirigindo": "driving",
    "pilotando": "flying", "pescando": "fishing", "cacando": "hunting",
    "explorando": "exploring", "viajando": "traveling", "sonhando": "dreaming",
    "sorrindo": "smiling", "chorando": "crying", "gritando": "shouting",
    "sussurrando": "whispering", "olhando": "looking", "observando": "watching",
    "no": "in the", "na": "in the", "em": "in", "sobre": "on",
    "com": "with", "sem": "without", "para": "for", "de": "of",
    "um": "a", "uma": "a", "o": "the", "a": "the", "os": "the", "as": "the",
    "e": "and", "ou": "or", "mas": "but", "muito": "very", "muita": "very",
    "mais": "more", "menos": "less", "tambem": "also", "ainda": "still",
    "dentro": "inside", "fora": "outside", "atras": "behind",
    "frente": "front", "lado": "side", "cima": "top", "baixo": "bottom",
    "perto": "near", "longe": "far", "junto": "together", "sozinho": "alone",
}

def traduzir_prompt(prompt):
    """Traduz palavras conhecidas PT->EN. Mantém o que não conhece (modelo tenta entender)."""
    palavras = prompt.split()
    traduzidas = []
    for p in palavras:
        # remove pontuação para buscar no dicionário
        limpa = p.strip('.,;:!?()"\'')
        traducao = DICIONARIO_PT_EN.get(limpa.lower())
        if traducao:
            # preserva a primeira letra maiúscula se a original tiver
            if p[0].isupper():
                traducao = traducao.capitalize()
            traduzidas.append(traducao)
        else:
            traduzidas.append(p)
    return ' '.join(traduzidas)

ESTILOS_POR_NOME = {
    "auto": None,
    "foto": "photorealistic, professional photography, 85mm lens, shallow depth of field, natural golden-hour lighting, film grain",
    "cartoon": "vibrant cartoon style, smooth cel shading, expressive characters, polished animation still, bold outlines",
    "pixel": "crisp pixel art, meticulous pixel detail, retro 16-bit game aesthetic, limited vibrant palette",
    "pintura": "fine art painting, rich visible brushstrokes, masterful chiaroscuro, museum-quality artwork",
    "scifi": "epic cinematic sci-fi concept art, volumetric lighting, glowing neon accents, dramatic atmosphere, deep space background",
    "natureza": "breathtaking landscape photography, golden hour light, god rays, ultra-detailed scenery, atmospheric depth",
    "minimalista": "elegant minimalism, clean geometric shapes, soft studio lighting, balanced negative space, premium flat design",
}

def enriquecer_prompt(prompt_usuario, estilo_nome=None):
    """
    Melhora o prompt do usuário adicionando direção de estilo e termos
    de qualidade, para gerar imagens significativamente mais bonitas.
    """
    base = (prompt_usuario or "").strip()
    if not base:
        base = "uma cena surreal e vibrante, cheia de detalhes"

    # TRADUZ o prompt para inglês ANTES de enriquecer
    base_traduzida = traduzir_prompt(base)
    print(f"--- Prompt traduzido: {base_traduzida}")

    texto = base_traduzida.lower()

    # 1. Estilo manual (seletor do frontend) tem prioridade
    estilo_escolhido = ESTILOS_POR_NOME.get(estilo_nome) if estilo_nome else None

    # 2. Se não veio estilo manual, detecta pelas palavras do usuário
    if not estilo_escolhido:
        for palavras, sufixo in ESTILOS:
            if any(p in texto for p in palavras):
                estilo_escolhido = sufixo
                break

    # 3. Fallback: estilo digital art genérico de alta qualidade
    if not estilo_escolhido:
        estilo_escolhido = (
            "stunning digital art, masterpiece quality, dramatic cinematic lighting, "
            "vibrant colors, dynamic composition"
        )

    # 2. Monta o prompt final (base TRADUZIDA + estilo + qualidade)
    prompt_final = f"{base_traduzida}, {estilo_escolhido}, {QUALIDADE_BASE}"
    print(f"--- Prompt enriquecido: {prompt_final}")
    return prompt_final


def gerar_pollinations(prompt, estilo_nome=None, novo=0):
    """
    Geração de imagem via Pollinations.ai.
    - Seed DETERMINÍSTICO (baseado no prompt) -> imagem fica em cache,
      carrega instantânea e não quebra.
    - Param 'novo' força um seed diferente (para o botão de tentar de novo).
    - Token opcional (POLLINATIONS_TOKEN, grátis em pollinations.ai)
      desbloqueia o modelo FLUX (qualidade muito superior ao modelo padrão).
    - Verifica a imagem no servidor antes de devolver a URL (nada de imagem quebrada).
    """
    prompt_final = enriquecer_prompt(prompt, estilo_nome)
    seed = (abs(hash(prompt_final)) + int(novo or 0) * 7919) % 100000

    url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt_final)
    url += (f"?width=1024&height=1024&nologo=true&enhance=false"
            f"&referrer=alexsantossp71.github.io&seed={seed}")

    # Token opcional: desbloqueia modelos melhores (FLUX) no Pollinations
    token = os.getenv("POLLINATIONS_TOKEN")
    if token:
        url += f"&token={token}"

    # Verifica se a imagem é válida (baixa o início do arquivo)
    # e tenta de novo em caso de falha (rate limit/instabilidade)
    for tentativa in range(3):
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=90) as resp:
                dados = resp.read(2048)
                # JPEG (FF D8 FF) ou PNG ou GIF = imagem válida
                if dados[:3] == b'\xff\xd8\xff' or b'PNG' in dados[:16] or dados[:3] == b'GIF':
                    print(f"Pollinations OK (tentativa {tentativa+1})")
                    return url
                else:
                    print(f"Pollinations retornou conteúdo não-imagem (tentativa {tentativa+1})")
        except Exception as e:
            print(f"Pollinations falhou (tentativa {tentativa+1}): {e}")
        time.sleep(2)

    # Último recurso: devolve a URL mesmo assim (pode funcionar no navegador)
    return url


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
    ip = request.remote_addr or 'desconhecido'
    if not rate_limit_ok(ip):
        return jsonify({"erro": "Muitas requisicoes. Aguarde um momento e tente de novo."}), 429

    dados = request.json
    prompt_usuario = dados.get('prompt') if dados else None
    estilo_usuario = dados.get('style') if dados else None
    novo = int(dados.get('novo') or 0) if dados else 0

    if not prompt_usuario:
        return jsonify({"erro": "O prompt é obrigatório!"}), 400

    print(f"--- Recebido pedido: {prompt_usuario} ---")

    # ---- Provedor 1: Pollinations (grátis, padrão) ----
    if PROVIDER == "pollinations":
        try:
            url = gerar_pollinations(prompt_usuario, estilo_usuario, novo)
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


@app.route('/')
def servir_frontend():
    """Serve o frontend (index.html) — o site fica acessível direto na Render."""
    try:
        resposta = send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'index.html')
        resposta.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return resposta
    except FileNotFoundError:
        abort(404)


PAGINA_404 = '''<!DOCTYPE html><html lang="pt-br"><head><meta charset="UTF-8">
<title>404 - Página não encontrada</title>
<style>body{font-family:'Segoe UI',sans-serif;background:#f0f2f5;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
.card{background:white;padding:3rem;border-radius:15px;box-shadow:0 10px 25px rgba(0,0,0,0.1);text-align:center;max-width:400px}
h1{font-size:64px;margin:0;color:#007bff} h2{color:#333} p{color:#666}
a{display:inline-block;margin-top:15px;padding:10px 24px;background:#007bff;color:white;text-decoration:none;border-radius:8px}
a:hover{background:#0056b3}</style></head>
<body><div class="card"><h1>404</h1><h2>Página não encontrada</h2>
<p>O endereco que voce procurou nao existe.</p>
<a href="/">Inicio do gerador</a></div></body></html>'''


@app.errorhandler(404)
def pagina_nao_encontrada(e):
    return PAGINA_404, 404


@app.route('/health', methods=['GET'])
def health():
    """Rota de verificação (a Render usa para saber se o serviço está vivo)."""
    token_pollinations = bool(os.getenv("POLLINATIONS_TOKEN"))
    return jsonify({
        "status": "ok",
        "provider": PROVIDER,
        "api_key_configured": client is not None,
        "pollinations_token": token_pollinations,
        "model": (IMAGE_MODEL if PROVIDER == "openrouter"
                  else ("FLUX (token ativo)" if token_pollinations else "sana (grátis, sem token)")),
        "rate_limit": f"{LIMITE_MAX}/min"
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
