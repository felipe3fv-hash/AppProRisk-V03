"""Guarda do ambiente.

Duas coisas que já morderam este projeto e que agora reprovam em vez de passar
despercebidas:

1. `tests/test_interface.py` usa `pytest.importorskip`. Se o Streamlit faltar no
   ambiente, aquele arquivo inteiro é PULADO e a execução fica verde mesmo sem
   ter testado a interface. Aqui isso vira falha.
2. As versões em `requirements.txt` estão fixadas para que um laudo seja
   reproduzível. Pino que ninguém confere é decoração: este arquivo compara o
   que está instalado com o que está fixado.
"""

from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
REQUISITOS = RAIZ / "requirements.txt"

_LINHA = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s#]+)")


def _pinos() -> list[tuple[str, str]]:
    if not REQUISITOS.exists():
        return []
    achados = []
    for linha in REQUISITOS.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        m = _LINHA.match(linha)
        if m:
            achados.append((m.group(1), m.group(2)))
    return achados


def test_requirements_tem_versoes_fixadas():
    pinos = _pinos()
    assert pinos, "requirements.txt não tem nenhuma dependência fixada com =="
    assert {n.lower() for n, _ in pinos} >= {"streamlit", "pandas", "reportlab"}


@pytest.mark.parametrize("pacote,esperado", _pinos() or [("streamlit", "")])
def test_dependencia_instalada_na_versao_fixada(pacote, esperado):
    try:
        instalado = version(pacote)
    except PackageNotFoundError:
        pytest.fail(
            f"'{pacote}' está em requirements.txt mas não está instalado neste "
            "ambiente. Rode: pip install -r requirements-dev.txt"
        )
    assert instalado == esperado, (
        f"'{pacote}' instalado na versão {instalado}, mas requirements.txt fixa "
        f"{esperado}. Alinhe os dois antes de emitir laudo — a versão das "
        "bibliotecas faz parte da reprodutibilidade do documento."
    )


def test_streamlit_importavel_para_os_testes_de_interface():
    """Sem esta guarda, um ambiente sem Streamlit pularia test_interface.py
    inteiro e a suíte continuaria verde."""
    import streamlit  # noqa: F401
    from streamlit.testing.v1 import AppTest  # noqa: F401


def test_pacote_spda_importavel():
    """Reprova cedo, com mensagem clara, quando o `pythonpath` do pytest.ini
    não estiver valendo — foi o que quebrou a CI da primeira vez."""
    import spda  # noqa: F401
    from spda import analise, eventos, ng, perdas, probabilidades, tabelas  # noqa: F401


def test_tabela_do_anexo_f_presente():
    csv = RAIZ / "dados" / "ng_municipios.csv"
    assert csv.exists(), (
        "dados/ng_municipios.csv não encontrado. Sem a Tabela F.1 o app não "
        "opera: N_G só pode vir do Anexo F (A.1.3)."
    )
    linhas = csv.read_text(encoding="utf-8").strip().splitlines()
    assert len(linhas) > 5500, f"Tabela F.1 incompleta: {len(linhas) - 1} municípios."
