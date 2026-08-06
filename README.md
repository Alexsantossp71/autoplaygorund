# 🎨 AutoPlayground — Gerador de Imagens com IA

> Descreva uma ideia em português e receba uma imagem gerada por IA em segundos. **Grátis, sem cadastro.**

🔗 **Site no ar:** https://autoplaygorund-api.onrender.com/

---

## ✨ Funcionalidades

- 🖼️ **Geração de imagens** a partir de prompt em **português**
- 🇧🇷 **Tradutor PT→EN embutido** (350+ palavras) — a IA entende exatamente o que você pediu
- 🎨 **Seletor de estilo manual**: automático, foto realista, cartoon/anime, pixel art, pintura, sci-fi, natureza, minimalista
- ✨ **Enriquecimento automático de prompts** — detecta o estilo e adiciona termos de qualidade estética
- 🖼️ **Galeria local** das suas criações (localStorage, até 30 imagens, modal ampliado, download)
- 🎲 **Botão "Variar"** — gera uma variação do mesmo prompt com seed diferente
- 🔄 **Retry automático** (3x) se a imagem falhar; verificação no servidor antes de exibir
- 🛡️ **Rate limit** (10 req/min por IP) — proteção da API pública
- 📱 Design responsivo (funciona no celular)

## 🛠️ Tecnologias

| Camada | Stack |
|---|---|
| Frontend | HTML + CSS + JavaScript vanilla (arquivo único) |
| Backend | **Python / Flask** |
| Geração de imagem | **Pollinations.ai** (grátis) — modelo FLUX com token, "sana" sem token |
| Deploy | **Render** (grátis) + GitHub Pages (alternativo) |
| Qualidade | **pytest** (18 testes) + **GitHub Actions** (CI) |

## 🧠 Como funciona

```
Você digita: "uma porta"
      ↓
[Tradutor PT→EN]  →  "a door"
      ↓
[Enriquecimento]  →  "a door, stunning digital art, masterpiece quality, ..."
      ↓
[Pollinations]    →  🚪 imagem 1024px em ~6s
```

## 🚀 Deploy na Render (grátis)

1. Crie conta grátis em **render.com** (logando com o GitHub)
2. **New → Blueprint** → selecione este repositório (lê o `render.yaml`)
3. Aguarde o build (~2 min)

### Variáveis de ambiente (opcionais)

| Variável | Para quê |
|---|---|
| `POLLINATIONS_TOKEN` | **Recomendado** — token grátis (pollinations.ai) que desbloqueia o modelo **FLUX** (qualidade muito superior) |
| `IMAGE_PROVIDER` | `pollinations` (padrão) ou `openrouter` |
| `OPENROUTER_API_KEY` | Chave do OpenRouter (se usar `IMAGE_PROVIDER=openrouter`) |
| `IMAGE_MODEL` | Modelo do OpenRouter (padrão: `google/gemini-3.1-flash-lite-image`) |
| `MAX_TOKENS` | Limite de tokens do OpenRouter (padrão: 8000) |
| `RATE_LIMIT_MAX` / `RATE_LIMIT_WINDOW` | Limite de requisições (padrão: 10/min) |

## 🚀 Como executar localmente

```bash
git clone https://github.com/Alexsantossp71/autoplaygorund.git
cd autoplaygorund

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python app.py
# servidor em http://localhost:5000
```

## 🧪 Testes

```bash
pip install pytest
pytest -v
# 18 testes: tradutor PT→EN, enriquecimento, extração de URL, rate limit, rotas
```

O CI roda os testes automaticamente a cada push (`.github/workflows/ci.yml`).

## 🔍 Endpoints

| Rota | Método | Descrição |
|---|---|---|
| `/` | GET | Frontend (página principal) |
| `/gerar` | POST | Gera imagem — body: `{"prompt": "...", "style": "...", "novo": 0}` |
| `/health` | GET | Status do serviço (provedor, token, modelo, rate limit) |

## 📁 Estrutura

```
autoplaygorund/
├── app.py             # Backend Flask (457+ linhas)
├── index.html         # Frontend completo (estilos + galeria + JS)
├── test_app.py        # 18 testes automatizados
├── render.yaml        # Deploy Blueprint (Render)
├── requirements.txt   # Dependências
├── .github/workflows/ # CI (testes) + Pages
└── .env.example       # Modelo de variáveis de ambiente
```

## 📜 Changelog

| Data | Mudança |
|---|---|
| ago/2026 | **v1.2** — tradutor PT→EN, botão Variar, SEO, rate limit, 404, 18 testes, CI |
| ago/2026 | **v1.1** — seletor de estilo manual, galeria, retry, seed determinístico, deploy Render |
| ago/2026 | **v1.0** — correção do modelo (FLUX → Gemini → Pollinations), deploy permanente |
| jan/2026 | **v0.1** — protótipo original (Codespace + OpenRouter) |

## 👤 Autor

**Alexandre Ramos** — [github.com/Alexsantossp71](https://github.com/Alexsantossp71)

## 📄 Licença

MIT © 2026 Alexandre Ramos
