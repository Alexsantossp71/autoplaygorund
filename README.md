# 🎨 AutoPlayground — Gerador de Imagens com IA

> Frontend HTML + backend Flask que gera imagens via OpenRouter (modelo FLUX schnell).

## 📌 Sobre

Aplicação simples que permite descrever uma imagem em texto e receber uma imagem gerada por inteligência artificial. O frontend envia o prompt para uma API **Flask**, que chama o modelo **FLUX schnell** através do **OpenRouter**.

## ✨ Funcionalidades

- 🖼️ Geração de imagens a partir de prompt de texto
- ✨ **Enriquecimento automático de prompts** — detecta o estilo (foto, cartoon, pixel art, pintura, sci-fi, natureza...) e adiciona termos de qualidade estética
- 🎨 Imagens em **1024×1024** com modelo FLUX (via Pollinations.ai, 100% grátis)
- 🔐 Chave de API protegida — lida de **variável de ambiente** (nunca fica no frontend)
- 🌐 CORS habilitado — o frontend pode ser servido do GitHub Pages
- 📝 Validação de prompt e tratamento de erros da IA
- 🆓 **Sem custo** — geração via Pollinations.ai (não precisa de chave nem créditos)
- 🔀 Provedor alternativo OpenRouter (via variável `IMAGE_PROVIDER=openrouter`)

## 🛠️ Tecnologias

- **Python / Flask** (backend)
- **OpenAI SDK** (cliente OpenRouter)
- **OpenRouter + FLUX schnell** (modelo de geração)
- HTML + CSS vanilla (frontend)

## 🚀 Como executar localmente

```bash
# 1. Clone o repositório
git clone https://github.com/Alexsantossp71/autoplaygorund.git
cd autoplaygorund

# 2. Crie o ambiente virtual e instale as dependências
python -m venv .venv
source .venv/bin/activate     # Linux/macOS
# .venv\Scripts\activate      # Windows
pip install flask flask-cors openai

# 3. Configure a chave do OpenRouter
export OPENROUTER_API_KEY="sua-chave-aqui"   # Linux/macOS
# set OPENROUTER_API_KEY=...                 # Windows (cmd)

# 4. Rode o servidor
python app.py
# servidor em http://localhost:5000
```

## 📁 Estrutura

```
autoplaygorund/
├── app.py           # API Flask (rotas POST /gerar e GET /health)
├── index.html       # Frontend (envia o prompt e exibe a imagem)
├── requirements.txt # Dependências Python
├── render.yaml      # Deploy automático na Render
└── .env.example     # Modelo de variáveis de ambiente
```

## 🧠 Como funciona o enriquecimento de prompt

Quando o usuário digita um prompt simples (ex.: "um gato astronauta"), o backend o transforma em:

```
um gato astronauta, stunning digital art, masterpiece quality, dramatic cinematic lighting,
vibrant colors, dynamic composition, ultra high resolution, sharp focus, intricate details,
professional color grading, award-winning composition
```

**Estilos detectados automaticamente:** foto/realista (85mm lens, golden-hour), cartoon/anime (cel shading), pixel art (16-bit), pintura (brushstrokes, chiaroscuro), sci-fi/cyberpunk (volumetric lighting, neon), natureza (god rays), minimalista (flat design).

## 🚀 Deploy na Render (grátis)

O arquivo `render.yaml` configura o deploy automático:

1. Crie uma conta grátis em **render.com** (pode logar com o GitHub)
2. No dashboard: **New → Blueprint**
3. Selecione este repositório — a Render lê o `render.yaml` e cria o serviço
4. Aguarde o build (~2 min) — o serviço fica em `https://autoplaygorund-api.onrender.com`
5. **Defina a chave:** Dashboard → `autoplaygorund-api` → **Environment** → adicione `OPENROUTER_API_KEY` (crie em openrouter.ai/keys) → **Deploy** (ou aguarde o redeploy automático)

> ⚠️ Se a URL gerada pela Render for diferente de `https://autoplaygorund-api.onrender.com`, atualize a constante `URL_DO_BACKEND` no `index.html`.

## 🔍 Testes

O backend tem uma rota de saúde: `GET /health` → `{"status": "ok", "api_key_configured": true/false}`

## 👤 Autor

**Alexandre Ramos** — [github.com/Alexsantossp71](https://github.com/Alexsantossp71)

## 📄 Status

Projeto de estudo funcional (deploy preparado para Render — agosto/2026).
