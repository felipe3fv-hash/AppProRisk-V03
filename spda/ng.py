"""Anexo F — densidade de descargas atmosféricas N_G por município.

A.1.3 e F.1.1 são categóricas: os valores de N_G devem ser iguais aos do Anexo F,
e "dados obtidos de outras fontes não podem ser utilizados". Este módulo é a
única porta de entrada de N_G no motor.

Sobrescrita manual continua possível — a autoridade com jurisdição pode impor
outro valor — mas exige justificativa textual, que é carimbada no laudo.
"""

from __future__ import annotations

import csv
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_CSV = Path(__file__).resolve().parent.parent / "dados" / "ng_municipios.csv"


@dataclass(frozen=True)
class Municipio:
    nome: str
    uf: str
    ng: float

    @property
    def rotulo(self) -> str:
        return f"{self.nome} — {self.uf}"


def _normaliza(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.casefold().strip()


@lru_cache(maxsize=1)
def carregar() -> tuple[Municipio, ...]:
    if not _CSV.exists():
        raise FileNotFoundError(
            f"Tabela F.1 não encontrada em {_CSV}. O motor não opera sem ela."
        )
    linhas = []
    with _CSV.open(encoding="utf-8", newline="") as f:
        for reg in csv.DictReader(f):
            linhas.append(Municipio(reg["municipio"], reg["uf"], float(reg["ng"])))
    if len(linhas) < 5000:
        raise ValueError(
            f"Tabela F.1 incompleta: {len(linhas)} municípios (esperado ~5 570)."
        )
    return tuple(sorted(linhas, key=lambda m: (m.uf, _normaliza(m.nome))))


@lru_cache(maxsize=1)
def ufs() -> tuple[str, ...]:
    return tuple(sorted({m.uf for m in carregar()}))


def municipios_da_uf(uf: str) -> tuple[Municipio, ...]:
    return tuple(m for m in carregar() if m.uf == uf)


def buscar(nome: str, uf: str) -> Municipio:
    alvo = _normaliza(nome)
    for m in municipios_da_uf(uf):
        if _normaliza(m.nome) == alvo:
            return m
    raise KeyError(f"Município '{nome}/{uf}' não consta da Tabela F.1 do Anexo F.")


def procurar(termo: str, limite: int = 40) -> list[Municipio]:
    """Busca livre por trecho do nome, para o campo de pesquisa da interface."""
    t = _normaliza(termo)
    if not t:
        return []
    exatos = [m for m in carregar() if _normaliza(m.nome) == t]
    inicio = [m for m in carregar() if _normaliza(m.nome).startswith(t) and m not in exatos]
    contem = [
        m for m in carregar()
        if t in _normaliza(m.nome) and m not in exatos and m not in inicio
    ]
    return (exatos + inicio + contem)[:limite]
