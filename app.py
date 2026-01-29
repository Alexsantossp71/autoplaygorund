import os
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
# Habilita CORS para aceitar pedidos do seu GitHub Pages
CORS(app)

# 1. Pega a chave dos Secrets do GitHub
api_key = os.getenv("OPENROUTER_API_KEY")

# Verificação de segurança para te avisar se a chave falhar
if not api_key:
    print("ERRO CRÍTICO: A variável 'OPENROUTER_API_KEY' não foi encontrada.")
    print("Dica: Se você acabou de adicionar o Secret, feche e abra o Codespace ou use o comando 'Reload Window'.")

# 2. Configura o cliente para o OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

@app.route('/gerar', methods=['POST'])
def gerar_imagem():
    dados = request.json
    prompt_usuario = dados.get('prompt')

    if not prompt_usuario:
        return jsonify({"erro": "O prompt é obrigatório!"}), 400

    print(f"--- Recebido pedido: {prompt_usuario} ---")

    try:
        # 3. Chama o modelo FLUX via OpenRouter
        completion = client.chat.completions.create(
            model="black-forest-labs/flux-1-schnell", # Modelo rápido e barato de imagem
            messages=[
                {
                    "role": "user",
                    "content": prompt_usuario
                }
            ],
        )

        # 4. Processa a resposta
        # O OpenRouter geralmente devolve a imagem como um link Markdown no texto
        conteudo_resposta = completion.choices[0].message.content
        print(f"Resposta bruta da IA: {conteudo_resposta}")

        # Tenta extrair a URL usando Regex (funciona para 'https://...' ou '![img](https://...)')
        url_match = re.search(r'(https?://[^\s)]+)', conteudo_resposta)

        if url_match:
            url_limpa = url_match.group(1)
            # Remove caracteres estranhos no final se houver (comum em markdown)
            url_limpa = url_limpa.rstrip(')') 
            return jsonify({"url": url_limpa})
        else:
            # Se não achou link, devolve o erro que a IA deu (ex: filtro de conteúdo)
            return jsonify({"erro": "A IA não retornou uma imagem válida.", "detalhes": conteudo_resposta}), 500

    except Exception as e:
        print(f"Erro no servidor: {e}")
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    # Roda o servidor acessível externamente na porta 5000
    app.run(host='0.0.0.0', port=5000)
