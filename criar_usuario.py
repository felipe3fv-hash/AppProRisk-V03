#!/usr/bin/env python3
"""Gera o hash de senha para .streamlit/secrets.toml.

    python criar_usuario.py mariz

Cole a linha impressa na seção [usuarios] do arquivo de secrets. A senha nunca
é armazenada — apenas a derivação PBKDF2-HMAC-SHA256 com salt aleatório.
"""
import getpass
import sys

from spda.auth import ITERACOES, gerar_hash


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    usuario = sys.argv[1].strip()
    s1 = getpass.getpass(f"Senha para '{usuario}': ")
    if len(s1) < 10:
        print("Use ao menos 10 caracteres.")
        return 1
    if s1 != getpass.getpass("Repita a senha: "):
        print("As senhas não conferem.")
        return 1
    print(f"\nAdicione em .streamlit/secrets.toml, sob [usuarios]:\n")
    print(f'{usuario} = "{gerar_hash(s1)}"')
    print(f"\n(PBKDF2-HMAC-SHA256, {ITERACOES:,} iterações, salt aleatório de 16 bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
