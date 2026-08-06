"""Testes automatizados do autoplaygorund.

Rode com: pip install -r requirements.txt pytest && pytest -v
"""
import importlib.util
import os
import sys
import time as _time

# Garante que o app seja importável (mesmo sem chaves configuradas)
os.environ.setdefault('IMAGE_PROVIDER', 'pollinations')
os.environ.pop('OPENROUTER_API_KEY', None)
os.environ.pop('POLLINATIONS_TOKEN', None)

spec = importlib.util.spec_from_file_location(
    'appmod', os.path.join(os.path.dirname(__file__), 'app.py')
)
appmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(appmod)


# ============ Testes do tradutor PT->EN ============

def test_tradutor_palavra_simples():
    assert appmod.traduzir_prompt('uma porta') == 'a door'


def test_tradutor_frase_completa():
    assert appmod.traduzir_prompt('cachorro correndo no parque') == 'dog running in the park'


def test_tradutor_mantem_palavras_desconhecidas():
    # "xylophone" não está no dicionário — deve permanecer
    resultado = appmod.traduzir_prompt('um xylophone roxo')
    assert 'xylophone' in resultado
    assert 'a' in resultado  # "um" foi traduzido


def test_tradutor_preserva_maiuscula():
    assert appmod.traduzir_prompt('Uma Porta') == 'A Door'


# ============ Testes do enriquecedor ============

def test_enriquecer_prompt_nao_vazio():
    resultado = appmod.enriquecer_prompt('um gato')
    assert len(resultado) > len('um gato')
    assert 'stunning digital art' in resultado.lower() or 'masterpiece' in resultado.lower()


def test_enriquecer_prompt_estilo_manual():
    resultado = appmod.enriquecer_prompt('um castelo', 'pixel')
    assert 'pixel art' in resultado.lower()


def test_enriquecer_prompt_deteccao_automatica():
    resultado = appmod.enriquecer_prompt('foto de um castelo', 'auto')
    assert 'photorealistic' in resultado.lower()


def test_enriquecer_prompt_prompt_vazio():
    resultado = appmod.enriquecer_prompt('', 'auto')
    assert 'surreal' in resultado.lower()


# ============ Testes da extração de URL ============

class FakeMessage:
    def __init__(self, content):
        self.content = content
        self.images = None


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeCompletion:
    def __init__(self, content):
        self.choices = [FakeChoice(content)]


def test_extrair_url_markdown():
    comp = FakeCompletion('![img](https://exemplo.com/imagem.jpg) texto')
    assert appmod.extrair_url_imagem(comp) == 'https://exemplo.com/imagem.jpg'


def test_extrair_url_solta():
    comp = FakeCompletion('veja: https://exemplo.com/arte.png fim')
    assert appmod.extrair_url_imagem(comp) == 'https://exemplo.com/arte.png'


def test_extrair_url_ausente():
    comp = FakeCompletion('sem url aqui')
    assert appmod.extrair_url_imagem(comp) is None


# ============ Testes do rate limit ============

def test_rate_limit_ok_primeira_vez():
    assert appmod.rate_limit_ok('ip-teste-1') is True


def test_rate_limit_bloqueia_apos_maximo():
    appmod._limite_requisicoes['ip-teste-2'] = [_time.time() for _ in range(appmod.LIMITE_MAX)]
    assert appmod.rate_limit_ok('ip-teste-2') is False


# ============ Testes das rotas ============

def test_health_ok():
    with appmod.app.test_client() as cliente:
        resp = cliente.get('/health')
        assert resp.status_code == 200
        dados = resp.get_json()
        assert dados['status'] == 'ok'
        assert 'provider' in dados


def test_gerar_sem_prompt_400():
    with appmod.app.test_client() as cliente:
        resp = cliente.post('/gerar', json={})
        assert resp.status_code == 400


def test_gerar_sem_prompt_texto_400():
    with appmod.app.test_client() as cliente:
        resp = cliente.post('/gerar', json={'prompt': ''})
        assert resp.status_code == 400


def test_404_amigavel():
    with appmod.app.test_client() as cliente:
        resp = cliente.get('/rota-inexistente')
        assert resp.status_code == 404
        assert '404' in resp.get_data(as_text=True)


def test_raiz_serve_frontend():
    with appmod.app.test_client() as cliente:
        resp = cliente.get('/')
        assert resp.status_code == 200
        assert 'Gerador' in resp.get_data(as_text=True)
