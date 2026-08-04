# 🎨 AutoPlayground — Gerador de Imagens com IA

> Frontend HTML + backend Flask que gera imagens via OpenRouter (modelo FLUX schnell).

## 📌 Sobre

Aplicação simples que permite descrever uma imagem em texto e receber uma imagem gerada por inteligência artificial. O frontend envia o prompt para uma API **Flask**, que chama o modelo **FLUX schnell** através do **OpenRouter**.

## ✨ Funcionalidades

- 🖼️ Geração de imagens a partir de prompt de texto
- 🔐 Chave de API protegida — lida de **variável de ambiente** (nunca fica no frontend)
- 🌐 CORS habilitado — o frontend pode ser servido do GitHub Pages
- 📝 Validação de prompt e tratamento de erros da IA

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
├── app.py        # API Flask (rota POST /gerar)
└── index.html    # Frontend (envia o prompt e exibe a imagem)
```

## 👤 Autor

**Alexandre Ramos** — [github.com/Alexsantossp71](https://github.com/Alexsantossp71)

## 📄 Status

Projeto de estudo funcional (última atualização: janeiro/2026).
