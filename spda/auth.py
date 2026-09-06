"""Autenticação: derivação de chave PBKDF2-HMAC-SHA256 e comparação constante.

Sem dependência externa (tudo vem da biblioteca padrão) e sem senha em claro em
lugar nenhum. O formato armazenado é:

    pbkdf2_sha256$<iteracoes>$<salt_b64>$<hash_b64>

`gerar_hash` é usado pelo utilitário `criar_usuario.py` para produzir a linha que
vai em `.streamlit/secrets.toml`. O aplicativo só conhece hashes.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from dataclasses import dataclass, field

ALGORITMO = "pbkdf2_sha256"
ITERACOES = 260_000
TAMANHO_SALT = 16

# Política de bloqueio por tentativas
MAX_TENTATIVAS = 5
JANELA_BLOQUEIO_S = 300      # 5 min
EXPIRACAO_SESSAO_S = 8 * 3600  # 8 h


def _b64e(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _b64d(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


def gerar_hash(senha: str, iteracoes: int = ITERACOES) -> str:
    salt = os.urandom(TAMANHO_SALT)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, iteracoes)
    return f"{ALGORITMO}${iteracoes}${_b64e(salt)}${_b64e(dk)}"


def verificar(senha: str, armazenado: str) -> bool:
    """Comparação em tempo constante. Nunca levanta para entrada malformada —
    apenas devolve False, para não vazar informação pelo tipo de erro."""
    try:
        algo, it, salt_b64, hash_b64 = armazenado.split("$")
        if algo != ALGORITMO:
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", senha.encode("utf-8"), _b64d(salt_b64), int(it)
        )
        return hmac.compare_digest(dk, _b64d(hash_b64))
    except Exception:
        # Custo artificial para que uma entrada malformada não seja
        # distinguível de uma senha errada pelo tempo de resposta.
        hashlib.pbkdf2_hmac("sha256", b"x", b"y" * TAMANHO_SALT, 1000)
        return False


@dataclass
class ControleTentativas:
    """Bloqueio por usuário após MAX_TENTATIVAS falhas dentro da janela."""

    falhas: dict[str, list[float]] = field(default_factory=dict)

    def bloqueado_ate(self, usuario: str) -> float | None:
        agora = time.time()
        marcas = [t for t in self.falhas.get(usuario, []) if agora - t < JANELA_BLOQUEIO_S]
        self.falhas[usuario] = marcas
        if len(marcas) >= MAX_TENTATIVAS:
            return marcas[0] + JANELA_BLOQUEIO_S
        return None

    def registrar_falha(self, usuario: str) -> None:
        self.falhas.setdefault(usuario, []).append(time.time())

    def limpar(self, usuario: str) -> None:
        self.falhas.pop(usuario, None)


def sessao_expirada(inicio_epoch: float) -> bool:
    return (time.time() - inicio_epoch) > EXPIRACAO_SESSAO_S
