"""Serialização do projeto e impressão digital dos dados de entrada.

Dois requisitos de produto resolvidos aqui:

  · o projetista salva, reabre e compara cenários (com e sem medidas de
    proteção — o procedimento de D.2), em vez de perder tudo num F5;
  · o laudo carrega um hash SHA-256 dos dados de entrada, de modo que qualquer
    pessoa possa provar, anos depois, que o arquivo de projeto que tem em mãos
    é exatamente o que gerou aquele documento.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, fields, is_dataclass
from typing import Any

from .modelo import (
    Estrutura,
    EstruturaAdjacente,
    Identificacao,
    LinhaEletrica,
    Projeto,
    SistemaInterno,
    Trecho,
    ZonaEstudo,
)
from .versao import NORMA_APLICADA, VERSAO_MOTOR

FORMATO = 2


def para_dict(projeto: Projeto) -> dict[str, Any]:
    return {
        "formato": FORMATO,
        "versao_motor": VERSAO_MOTOR,
        "norma": NORMA_APLICADA,
        "projeto": asdict(projeto),
    }


def para_json(projeto: Projeto, indent: int = 2) -> str:
    return json.dumps(para_dict(projeto), ensure_ascii=False, indent=indent)


def _construir(cls, dados: dict) -> Any:
    """Reconstrói uma dataclass ignorando chaves desconhecidas, para que um
    arquivo salvo por uma versão anterior ainda abra."""
    validos = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in dados.items() if k in validos})


def de_dict(dados: dict[str, Any]) -> Projeto:
    p = dict(dados.get("projeto", dados))

    ident = _construir(Identificacao, p.pop("identificacao", {}) or {})
    est = _construir(Estrutura, p.pop("estrutura", {}) or {})

    zonas = []
    for zd in p.pop("zonas", []) or []:
        zd = dict(zd)
        sistemas = [_construir(SistemaInterno, s) for s in zd.pop("sistemas_internos", []) or []]
        z = _construir(ZonaEstudo, zd)
        z.sistemas_internos = sistemas
        zonas.append(z)

    linhas = []
    for ld in p.pop("linhas", []) or []:
        ld = dict(ld)
        trechos = [_construir(Trecho, t) for t in ld.pop("trechos", []) or []]
        adj_d = ld.pop("estrutura_adjacente", None)
        ln = _construir(LinhaEletrica, ld)
        ln.trechos = trechos or [Trecho()]
        ln.estrutura_adjacente = _construir(EstruturaAdjacente, adj_d) if adj_d else None
        linhas.append(ln)

    proj = _construir(Projeto, p)
    proj.identificacao = ident
    proj.estrutura = est
    proj.zonas = zonas
    proj.linhas = linhas
    return proj


def de_json(texto: str | bytes) -> Projeto:
    if isinstance(texto, bytes):
        texto = texto.decode("utf-8")
    return de_dict(json.loads(texto))


def impressao_digital(projeto: Projeto) -> str:
    """SHA-256 dos dados de entrada, normalizados e ordenados.

    Independe de espaçamento e de ordem de chaves, mas muda com qualquer
    alteração de valor. Os 16 primeiros dígitos vão para o rodapé do laudo.
    """
    canonico = json.dumps(
        _normalizar(asdict(projeto)), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def _normalizar(obj):
    """Normaliza para que 1 e 1.0 produzam a mesma impressão digital: são o
    mesmo dado de entrada. `bool` é subclasse de `int` e fica de fora."""
    if isinstance(obj, dict):
        return {k: _normalizar(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_normalizar(v) for v in obj]
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (int, float)):
        return round(float(obj), 10)
    return obj


def clonar(projeto: Projeto) -> Projeto:
    """Cópia profunda via serialização — base da comparação de cenários (D.2)."""
    return de_dict(para_dict(projeto))


__all__ = [
    "FORMATO", "para_dict", "para_json", "de_dict", "de_json",
    "impressao_digital", "clonar",
]


assert is_dataclass(Projeto)
