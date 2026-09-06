"""Envio da solicitação de acesso por e-mail.

Decisão de segurança que vale a pena entender antes de mexer aqui: o e-mail
NÃO leva a senha do solicitante. Leva a linha pronta para colar em
`[usuarios]` — usuário + derivação PBKDF2 — que é exatamente o que os segredos
precisam. Assim a senha de cada cliente não circula por caixa de entrada, não
fica em rascunho, não vaza junto com o Gmail.

Consequência prática, e é o comportamento correto: ninguém, nem o
administrador, consegue recuperar a senha de um cliente. Quem esquece a senha
faz uma nova solicitação.

Este módulo não importa Streamlit. A configuração chega de fora, para que o
motor continue testável sem interface.
"""

from __future__ import annotations

import re
import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage

DESTINATARIO_PADRAO = "proriskapp@gmail.com"
TIMEOUT_S = 20

_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
_RE_USUARIO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,31}$")


def email_valido(valor: str) -> bool:
    return bool(_RE_EMAIL.match((valor or "").strip()))


def usuario_valido(valor: str) -> bool:
    """3 a 32 caracteres, começando por letra ou número. Sem espaços nem acentos
    — é uma chave de TOML, e chave de TOML com espaço quebra os segredos."""
    return bool(_RE_USUARIO.match((valor or "").strip()))


@dataclass(frozen=True)
class ConfigEmail:
    remetente: str = ""
    senha_app: str = ""
    destinatario: str = DESTINATARIO_PADRAO
    servidor: str = "smtp.gmail.com"
    porta: int = 465

    @property
    def configurado(self) -> bool:
        return bool(self.remetente and self.senha_app and self.destinatario)


@dataclass(frozen=True)
class Solicitacao:
    nome: str
    email: str
    usuario: str
    credencial: str          # linha pronta: usuario = "pbkdf2_sha256$..."
    telefone: str = ""
    organizacao: str = ""
    crea: str = ""
    observacao: str = ""
    momento: str = ""

    def __post_init__(self) -> None:
        if not self.momento:
            object.__setattr__(
                self, "momento", datetime.now().strftime("%d/%m/%Y às %H:%M")
            )

    @property
    def assunto(self) -> str:
        return f"[SPDA Risk Pro] Solicitação de acesso — {self.nome} ({self.usuario})"

    def corpo_texto(self) -> str:
        linhas = [
            "Nova solicitação de acesso ao SPDA Risk Pro.",
            "",
            f"Nome ............: {self.nome}",
            f"E-mail ..........: {self.email}",
        ]
        if self.telefone:
            linhas.append(f"Telefone ........: {self.telefone}")
        if self.organizacao:
            linhas.append(f"Empresa .........: {self.organizacao}")
        if self.crea:
            linhas.append(f"CREA ............: {self.crea}")
        linhas += [
            f"Usuário desejado : {self.usuario}",
            f"Recebido em .....: {self.momento}",
        ]
        if self.observacao:
            linhas += ["", "Observação do solicitante:", self.observacao]
        linhas += [
            "",
            "-" * 62,
            "PARA LIBERAR O ACESSO",
            "-" * 62,
            "No painel do Streamlit: ⋮ → Settings → Secrets.",
            "Acrescente a linha abaixo DENTRO do bloco [usuarios] que já existe",
            "(se ainda não existir, crie o bloco com a primeira linha [usuarios]):",
            "",
            self.credencial,
            "",
            "Salve. O app reinicia sozinho e o acesso passa a valer.",
            "",
            "A senha escolhida pelo solicitante não está neste e-mail e não pode",
            "ser recuperada: o que vai acima é a derivação PBKDF2-HMAC-SHA256,",
            "da qual não se volta para a senha. Quem esquecer a senha faz uma",
            "nova solicitação.",
        ]
        return "\n".join(linhas)


def montar_mensagem(cfg: ConfigEmail, s: Solicitacao) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = s.assunto
    msg["From"] = cfg.remetente
    msg["To"] = cfg.destinatario
    if email_valido(s.email):
        msg["Reply-To"] = s.email
    msg.set_content(s.corpo_texto())
    return msg


def enviar(cfg: ConfigEmail, s: Solicitacao) -> tuple[bool, str]:
    """Retorna (sucesso, mensagem legível). Nunca levanta exceção.

    Falhar em enviar não pode derrubar a página: a interface tem um caminho
    alternativo (mostrar o bloco para o solicitante encaminhar), e é ele que
    entra em ação quando isto retorna False.
    """
    if not cfg.configurado:
        return False, "Envio de e-mail não configurado neste app."
    try:
        contexto = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            cfg.servidor, cfg.porta, context=contexto, timeout=TIMEOUT_S
        ) as smtp:
            smtp.login(cfg.remetente, cfg.senha_app)
            smtp.send_message(montar_mensagem(cfg, s))
        return True, "Solicitação enviada."
    except smtplib.SMTPAuthenticationError:
        return False, (
            "O servidor de e-mail recusou as credenciais. Verifique se a senha "
            "de aplicativo do Gmail continua válida."
        )
    except (smtplib.SMTPException, OSError, ssl.SSLError) as ex:
        return False, f"Não foi possível enviar o e-mail: {type(ex).__name__}."
