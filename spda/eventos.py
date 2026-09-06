"""Anexo A — número médio anual N de eventos perigosos.

Todas as equações do Anexo A vivem aqui, e em nenhum outro lugar. A versão
anterior recalculava N_L e N_I dentro do analisador, em três laços diferentes.
"""

from __future__ import annotations

from dataclasses import dataclass

from .modelo import Estrutura, LinhaEletrica, Projeto


@dataclass(frozen=True)
class EventosLinha:
    id_linha: str
    n_l: float      # eq. (A.7), somado sobre os trechos
    n_i: float      # eq. (A.9), somado sobre os trechos
    n_dj: float     # eq. (A.4)

    @property
    def n_l_mais_n_dj(self) -> float:
        return self.n_l + self.n_dj


def n_d(n_g: float, estrutura: Estrutura) -> float:
    """Eq. (A.3) — descargas na estrutura."""
    return n_g * estrutura.a_d() * estrutura.c_d * 1e-6


def n_m(n_g: float, estrutura: Estrutura) -> float:
    """Eq. (A.5) — descargas próximo da estrutura."""
    return n_g * estrutura.a_m() * 1e-6


def n_l(n_g: float, linha: LinhaEletrica) -> float:
    """Eq. (A.7) somada sobre os trechos S_L (6.4.3)."""
    return sum(
        n_g * t.a_l() * t.c_i * t.c_e * t.c_t * 1e-6 for t in linha.trechos
    )


def n_i(n_g: float, linha: LinhaEletrica) -> float:
    """Eq. (A.9) somada sobre os trechos S_L (6.5.3)."""
    return sum(
        n_g * t.a_i() * t.c_i * t.c_e * t.c_t * 1e-6 for t in linha.trechos
    )


def n_dj(n_g: float, linha: LinhaEletrica) -> float:
    """Eq. (A.4) — descargas na estrutura adjacente conectada pela linha.

    C_T é o da linha; havendo trechos com C_T diferentes, 6.8.2 manda adotar o
    valor que leva ao maior risco.
    """
    adj = linha.estrutura_adjacente
    if adj is None:
        return 0.0
    return n_g * adj.a_dj() * adj.c_dj * linha.c_t_mais_desfavoravel * 1e-6


def eventos_das_linhas(projeto: Projeto) -> dict[str, EventosLinha]:
    g = projeto.n_g
    return {
        ln.id_linha: EventosLinha(
            id_linha=ln.id_linha,
            n_l=n_l(g, ln),
            n_i=n_i(g, ln),
            n_dj=n_dj(g, ln),
        )
        for ln in projeto.linhas
    }
