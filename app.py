import os
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
# Habilita CORS para aceitar pedidos do seu GitHub Pages
CORS(app)

# 1. Pega a chave dos Secrets/Environment (Render, Codespaces, .env)
api_key = os.getenv("OPENROUTER_API_KEY")

# Modelo de geração de imagem no OpenRouter (o antigo flux-1-schnell saiu do catálogo)
# Opções atuais (ago/2026):
#   google/gemini-3.1-flash-lite-image  -> mais barato (recomendado)
#   google/gemini-3.1-flash-image       -> melhor qualidade
#   openai/gpt-5-image-mini             -> alternativa OpenAI
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "google/gemini-3.1-flash-lite-image")
# Limite de tokens de saída (o Gemini Image reserva muitos tokens; ajuste conforme seu crédito)
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "8000"))

# 2. Cliente OpenAI só é criado se a chave existir.
#    (Antes, sem chave, o servidor quebrava na inicialização)
client = None
if api_key:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
else:
    print("ERRO CRÍTICO: A variável 'OPENROUTER_API_KEY' não foi encontrada.")
    print("Dica Render: Dashboard -> autoplaygorund-api -> Environment -> Add")
    print("Dica local:  copie .env.example para .env e preencha a chave")


def extrair_url_imagem(completion):
    """
    Extrai a URL da imagem gerada, lidando com os formatos de resposta
    dos modelos de imagem do OpenRouter (Gemini Image, GPT Image etc).
    Retorna a URL da imagem, ou None se não encontrar.
    """
    try:
        msg = completion.choices[0].message

        # Formato 1: content como texto com Markdown ![alt](url) ou URL solta
        conteudo = getattr(msg, 'content', None)
        if isinstance(conteudo, list):  # alguns modelos retornam lista de partes
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
            # Markdown ![alt](url)
            m = re.search(r'!\[[^\]]*\]\((https?://[^\s)]+)\)', conteudo)
            if m:
                return m.group(1).rstrip(')')
            # URL solta
            m = re.search(r'(https?://[^\s)]+)', conteudo)
            if m:
                return m.group(1).rstrip(')')

        # Formato 2: campo 'images' do OpenRouter (lista de {url} ou {b64_json})
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

    if client is None:
        return jsonify({"erro": "Servidor sem chave de API configurada. Contate o administrador."}), 500

    print(f"--- Recebido pedido: {prompt_usuario} ---")

    try:
        # 3. Chama o modelo de imagem via OpenRouter
        completion = client.chat.completions.create(
            model=IMAGE_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt_usuario
                }
            ],
            # Sinaliza que a resposta deve incluir imagem (usado pelos modelos Gemini/GPT Image)
            modalities=["image", "text"],
            max_tokens=MAX_TOKENS,
        )

        # 4. Extrai a URL da imagem da resposta
        url_imagem = extrair_url_imagem(completion)
        print(f"Resposta da IA: {completion.choices[0].message.content}")

        if url_imagem:
            return jsonify({"url": url_imagem})
        else:
            return jsonify({"erro": "A IA não retornou uma imagem válida.",
                            "detalhes": str(getattr(completion.choices[0].message, 'content', ''))}), 500

    except Exception as e:
        print(f"Erro no servidor: {e}")
        return jsonify({"erro": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Rota de verificação (a Render usa para saber se o serviço está vivo)."""
    return jsonify({"status": "ok", "api_key_configured": client is not None, "model": IMAGE_MODEL})


if __name__ == '__main__':
    # Roda o servidor acessível externamente
    # Porta vem da variável de ambiente (Render usa PORT; local usa 5000)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
