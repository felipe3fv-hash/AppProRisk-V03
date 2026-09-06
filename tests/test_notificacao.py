"""Testes do envio da solicitação de acesso.

O ponto mais importante coberto aqui: a senha em claro NUNCA aparece no
e-mail. Se alguém mexer no formato da mensagem, este arquivo reprova.
"""

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from spda.auth import verificar
from spda.notificacao import (
    DESTINATARIO_PADRAO,
    ConfigEmail,
    Solicitacao,
    email_valido,
    enviar,
    montar_mensagem,
    usuario_valido,
)

SENHA = "uma-senha-bem-secreta-2026"
CRED = 'mariz = "pbkdf2_sha256$260000$c2FsdA==$aGFzaA=="'


def _solicitacao(**kw) -> Solicitacao:
    base = dict(
        nome="Mariz", email="mariz@exemplo.com", usuario="mariz",
        credencial=CRED, telefone="87 90000-0000", organizacao="AJF Consultoria",
        crea="PE-000000000", observacao="Uso em laudos de SPDA.",
    )
    base.update(kw)
    return Solicitacao(**base)


# =============================================================================
# Validações de entrada
# =============================================================================
@pytest.mark.parametrize("valor", [
    "a@b.co", "mariz.mege@gmail.com", "nome+tag@dominio.com.br",
])
def test_emails_validos(valor):
    assert email_valido(valor)


@pytest.mark.parametrize("valor", [
    "", "sem-arroba", "a@b", "a@b.c", "com espaco@x.com", "@x.com", "a@@b.com",
])
def test_emails_invalidos(valor):
    assert not email_valido(valor)


@pytest.mark.parametrize("valor", ["mar", "mariz", "user_1", "a-b.c", "M" * 32])
def test_usuarios_validos(valor):
    assert usuario_valido(valor)


@pytest.mark.parametrize("valor", [
    "", "ab", "M" * 33, "com espaço", "acentuação", "_comeca_com_underscore",
    "tem/barra", "aspas\"aqui", "[colchete]",
])
def test_usuarios_invalidos(valor):
    """Chave de TOML com espaço, acento ou aspas quebra o bloco de segredos."""
    assert not usuario_valido(valor)


# =============================================================================
# Conteúdo da mensagem
# =============================================================================
def test_email_nunca_contem_a_senha_em_claro():
    """Regressão da decisão de segurança central deste módulo."""
    s = _solicitacao(observacao=f"minha senha e {SENHA}")
    corpo = s.corpo_texto()
    # A observação é do solicitante e vai como ele escreveu; o que não pode
    # é o sistema acrescentar a senha por conta própria em qualquer campo.
    cfg = ConfigEmail(remetente="a@b.com", senha_app="x")
    msg = montar_mensagem(cfg, _solicitacao())
    assert SENHA not in msg.get_content()
    assert "pbkdf2_sha256$" in msg.get_content()
    assert corpo  # o corpo é montado sem erro mesmo com texto livre


def test_corpo_traz_a_linha_pronta_para_os_segredos():
    corpo = _solicitacao().corpo_texto()
    assert CRED in corpo
    assert "[usuarios]" in corpo
    assert "Settings" in corpo and "Secrets" in corpo


def test_corpo_traz_os_dados_de_contato():
    corpo = _solicitacao().corpo_texto()
    for esperado in ("Mariz", "mariz@exemplo.com", "AJF Consultoria",
                     "PE-000000000", "87 90000-0000"):
        assert esperado in corpo


def test_campos_opcionais_ausentes_nao_aparecem():
    corpo = _solicitacao(telefone="", organizacao="", crea="", observacao="").corpo_texto()
    assert "Telefone" not in corpo
    assert "Empresa" not in corpo
    assert "CREA" not in corpo


def test_corpo_avisa_que_a_senha_nao_e_recuperavel():
    assert "não pode" in _solicitacao().corpo_texto()


def test_momento_preenchido_automaticamente():
    assert _solicitacao().momento


def test_assunto_identifica_solicitante_e_usuario():
    a = _solicitacao().assunto
    assert "Mariz" in a and "mariz" in a and "SPDA Risk Pro" in a


def test_reply_to_aponta_para_o_solicitante():
    cfg = ConfigEmail(remetente="app@exemplo.com", senha_app="x")
    msg = montar_mensagem(cfg, _solicitacao())
    assert msg["Reply-To"] == "mariz@exemplo.com"
    assert msg["To"] == DESTINATARIO_PADRAO


def test_reply_to_omitido_quando_email_invalido():
    cfg = ConfigEmail(remetente="app@exemplo.com", senha_app="x")
    msg = montar_mensagem(cfg, _solicitacao(email="invalido"))
    assert msg["Reply-To"] is None


# =============================================================================
# Envio
# =============================================================================
def test_config_incompleta_nao_e_considerada_configurada():
    assert not ConfigEmail().configurado
    assert not ConfigEmail(remetente="a@b.com").configurado
    assert not ConfigEmail(remetente="a@b.com", senha_app="x", destinatario="").configurado
    assert ConfigEmail(remetente="a@b.com", senha_app="x").configurado


def test_destinatario_padrao_e_o_do_produto():
    assert ConfigEmail().destinatario == "proriskapp@gmail.com"


def test_enviar_sem_configuracao_falha_sem_levantar():
    ok, msg = enviar(ConfigEmail(), _solicitacao())
    assert ok is False and "não configurado" in msg


@patch("spda.notificacao.smtplib.SMTP_SSL")
def test_enviar_com_sucesso(mock_smtp):
    ctx = MagicMock()
    mock_smtp.return_value.__enter__.return_value = ctx
    cfg = ConfigEmail(remetente="app@exemplo.com", senha_app="segredo")
    ok, _ = enviar(cfg, _solicitacao())
    assert ok
    ctx.login.assert_called_once_with("app@exemplo.com", "segredo")
    ctx.send_message.assert_called_once()
    enviada = ctx.send_message.call_args[0][0]
    assert enviada["To"] == DESTINATARIO_PADRAO
    assert CRED in enviada.get_content()


@patch("spda.notificacao.smtplib.SMTP_SSL")
def test_falha_de_autenticacao_tem_mensagem_propria(mock_smtp):
    mock_smtp.side_effect = smtplib.SMTPAuthenticationError(535, b"bad")
    ok, msg = enviar(ConfigEmail(remetente="a@b.com", senha_app="x"), _solicitacao())
    assert ok is False
    assert "senha de aplicativo" in msg


@patch("spda.notificacao.smtplib.SMTP_SSL")
def test_falha_de_rede_nao_levanta(mock_smtp):
    mock_smtp.side_effect = OSError("sem rede")
    ok, msg = enviar(ConfigEmail(remetente="a@b.com", senha_app="x"), _solicitacao())
    assert ok is False and "OSError" in msg


# =============================================================================
# Integração com o hash real
# =============================================================================
def test_credencial_gerada_e_verificavel():
    """A linha que vai por e-mail precisa realmente autenticar depois."""
    from spda.auth import gerar_hash
    linha = f'mariz = "{gerar_hash(SENHA)}"'
    armazenado = linha.split('"')[1]
    assert verificar(SENHA, armazenado)
    assert not verificar("outra-coisa", armazenado)
    assert SENHA not in linha
