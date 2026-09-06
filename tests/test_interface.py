"""Smoke test da interface: o script roda de ponta a ponta sem exceção.

Usa o AppTest do próprio Streamlit — nenhum navegador envolvido. Garante que
uma alteração no modelo não quebre silenciosamente a tela.
"""

import time

import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")
AppTest = st_testing.AppTest

from spda.modelo import (  # noqa: E402
    Estrutura,
    Identificacao,
    LinhaEletrica,
    Projeto,
    SistemaInterno,
    Trecho,
    ZonaEstudo,
)


def _app_sem_usuarios():
    at = AppTest.from_file("app.py", default_timeout=90)
    at.secrets["usuarios"] = {}
    return at.run()


def _app(projeto=None):
    at = AppTest.from_file("app.py", default_timeout=90)
    at.session_state["usuario"] = "teste"
    at.session_state["inicio_sessao"] = time.time()
    if projeto is not None:
        at.session_state["projeto"] = projeto
    return at.run()


def _projeto_completo() -> Projeto:
    return Projeto(
        identificacao=Identificacao(obra="Teste", responsavel_tecnico="Eng.", crea="PE-1"),
        municipio="Petrolina", uf="PE", n_g=6.0, pessoas_total=20.0,
        p_b_chave="III", p_eb_chave="II", sistema_critico=True,
        estrutura=Estrutura(comprimento_m=40, largura_m=20, altura_m=10),
        linhas=[LinhaEletrica(id_linha="L1", trechos=[Trecho(comprimento_m=300)])],
        zonas=[ZonaEstudo(
            id_zona="Z1", ocupacao="comercial", pessoas_na_zona=20.0,
            sistemas_internos=[SistemaInterno(id_sistema="S1", uw_kv=2.5, ids_linhas=["L1"])],
        )],
    )


def test_app_carrega_sem_excecao_com_projeto_vazio():
    at = _app()
    assert not at.exception
    assert any("Análise de risco" in h.value for h in at.title)


def test_app_bloqueia_laudo_com_projeto_incompleto():
    at = _app()
    assert not at.exception
    assert any("impedem a emissão" in e.value for e in at.error)


def test_app_calcula_com_projeto_valido():
    at = _app(_projeto_completo())
    assert not at.exception
    rotulos = " ".join(m.label for m in at.metric)
    assert "R1" in rotulos and "R3" in rotulos and "R4" in rotulos


def test_app_nao_bloqueia_projeto_valido():
    at = _app(_projeto_completo())
    assert not at.exception
    assert not any("impedem a emissão" in e.value for e in at.error)


def test_app_exige_login_sem_sessao():
    at = AppTest.from_file("app.py", default_timeout=90).run()
    assert not at.exception
    # O st.stop() do login impede que o título da aplicação seja renderizado.
    assert not at.title


def test_login_avisa_quando_nao_ha_usuarios():
    at = AppTest.from_file("app.py", default_timeout=90)
    at.secrets["usuarios"] = {}
    at = at.run()
    assert not at.exception
    assert any("ainda não tem nenhum usuário" in i.value for i in at.info)


def test_aviso_some_quando_ha_usuarios():
    from spda.auth import gerar_hash

    at = AppTest.from_file("app.py", default_timeout=90)
    at.secrets["usuarios"] = {"mariz": gerar_hash("uma-senha-bem-longa")}
    at = at.run()
    assert not at.exception
    assert not any("ainda não tem nenhum usuário" in i.value for i in at.info)


def _preencher_solicitacao(at, **campos):
    dados = {
        "sol_nome": "Mariz Mege",
        "sol_email": "mariz@exemplo.com",
        "sol_usuario": "mariz",
        "sol_senha1": "uma-senha-bem-longa",
        "sol_senha2": "uma-senha-bem-longa",
    }
    dados.update(campos)
    for chave, valor in dados.items():
        at.text_input(key=chave).set_value(valor)
    return at


def _enviar(at):
    """O botão de envio é o último dos formulários da página de entrada."""
    return at.button[-1].click().run()


def test_solicitacao_gera_credencial_valida_e_verificavel():
    from spda.auth import verificar

    at = _app_sem_usuarios()
    at = _preencher_solicitacao(at)
    at = _enviar(at)
    assert not at.exception
    bloco = "\n".join(c.value for c in at.code)
    assert "[usuarios]" in bloco and "pbkdf2_sha256$" in bloco
    armazenado = bloco.split('"')[1]
    assert verificar("uma-senha-bem-longa", armazenado)
    assert not verificar("outra-senha", armazenado)


def test_solicitacao_nunca_exibe_a_senha_em_claro():
    at = _app_sem_usuarios()
    at = _preencher_solicitacao(at, sol_senha1="segredo-do-mariz-123",
                                sol_senha2="segredo-do-mariz-123")
    at = _enviar(at)
    tudo = " ".join(
        [c.value for c in at.code]
        + [m.value for m in at.markdown]
        + [w.value for w in at.warning]
        + [s_.value for s_ in at.success]
        + [cp.value for cp in at.caption]
    )
    assert "segredo-do-mariz-123" not in tudo


@pytest.mark.parametrize("campos,trecho", [
    ({"sol_nome": "Ma"}, "nome completo"),
    ({"sol_email": "sem-arroba"}, "e-mail válido"),
    ({"sol_usuario": "com espaço"}, "Usuário inválido"),
    ({"sol_senha1": "curta", "sol_senha2": "curta"}, "10 caracteres"),
    ({"sol_senha2": "diferente-mas-longa"}, "não são iguais"),
])
def test_solicitacao_recusa_dados_invalidos(campos, trecho):
    at = _app_sem_usuarios()
    at = _preencher_solicitacao(at, **campos)
    at = _enviar(at)
    assert not at.exception
    assert any(trecho in e.value for e in at.error), [e.value for e in at.error]


def test_sem_smtp_configurado_a_credencial_e_entregue_na_tela():
    """Sem e-mail, o solicitante ainda consegue encaminhar o bloco."""
    at = _app_sem_usuarios()
    at = _enviar(_preencher_solicitacao(at))
    assert any("Copie o bloco" in w.value or "envie para" in w.value
               for w in at.warning)
    assert any("pbkdf2_sha256$" in c.value for c in at.code)


def test_login_recusa_senha_errada():
    from spda.auth import gerar_hash

    at = AppTest.from_file("app.py", default_timeout=90)
    at.secrets["usuarios"] = {"mariz": gerar_hash("uma-senha-bem-longa")}
    at = at.run()
    at.text_input(key="login_usuario").set_value("mariz")
    at.text_input(key="login_senha").set_value("errada")
    at = at.button[0].click().run()
    assert any("inválidos" in e.value for e in at.error)
    assert not at.title


def test_login_aceita_senha_correta():
    from spda.auth import gerar_hash

    at = AppTest.from_file("app.py", default_timeout=90)
    at.secrets["usuarios"] = {"mariz": gerar_hash("uma-senha-bem-longa")}
    at = at.run()
    at.text_input(key="login_usuario").set_value("mariz")
    at.text_input(key="login_senha").set_value("uma-senha-bem-longa")
    at = at.button[0].click().run()
    assert not at.exception
    assert at.session_state["usuario"] == "mariz"
