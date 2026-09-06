"""Anexo B — probabilidades P_X de dano.

Duas regras de composição da norma são aplicadas literalmente aqui, e são o
coração da correção em relação à versão anterior:

  6.9.1.2 b) / 7.4.1.2 b)  P_C e P_M compõem-se sobre os SISTEMAS INTERNOS da
                           zona pelas equações (12) e (13) — nunca sobre linhas.

  6.9.1.2 a)               Para R_A, R_B, R_U, R_V, R_W e R_Z fixa-se UM valor
                           por zona para cada parâmetro; havendo mais de um
                           aplicável, adota-se o MAIOR.

Tudo é calculado por (zona, linha, sistema interno). Nenhum parâmetro de zona é
lido de outra zona.
"""

from __future__ import annotations

from . import tabelas as T
from .modelo import LinhaEletrica, Projeto, SistemaInterno, ZonaEstudo

# U_W de fallback quando a zona não declara sistema interno. É o pior caso
# razoável; a validação exige a declaração antes de emitir laudo.
UW_FALLBACK_KV = 1.0


def _sistemas(zona: ZonaEstudo) -> list[SistemaInterno]:
    return zona.sistemas_internos or []


def _c_ld_do_sistema(sistema: SistemaInterno, linhas: dict[str, LinhaEletrica]) -> float:
    """C_LD aplicável a um sistema interno, para o cálculo de P_C.

    B.4.4: os valores de C_LD da Tabela B.4 referem-se a sistemas internos
    BLINDADOS; para sistemas internos não blindados, C_LD = 1.
    """
    if sistema.sistema_independente and not sistema.ids_linhas:
        return 0.0  # Tabela B.4 — "sem conexões com linhas elétricas externas"
    if not sistema.blindado:
        return 1.0
    conectadas = [linhas[i] for i in sistema.ids_linhas if i in linhas]
    if not conectadas:
        return 0.0
    return max(ln.c_ld_c_li()[0] for ln in conectadas)


# =============================================================================
# S1 — descarga na estrutura
# =============================================================================
def p_a(projeto: Projeto, zona: ZonaEstudo) -> float:
    """Eq. (B.1) — P_A = P_TA × P_B."""
    return zona.p_ta * projeto.p_b


def p_b(projeto: Projeto) -> float:
    """Tabela B.2."""
    return projeto.p_b


def p_c_do_sistema(
    sistema: SistemaInterno, linhas: dict[str, LinhaEletrica]
) -> float:
    """Eq. (B.2) — P_C = P_SPD × C_LD, para um sistema interno."""
    return sistema.p_spd * _c_ld_do_sistema(sistema, linhas)


def p_c(zona: ZonaEstudo, linhas: dict[str, LinhaEletrica]) -> float:
    """Eq. (12) — P_C = 1 − Π(1 − P_Ci) sobre os sistemas internos da zona."""
    sistemas = _sistemas(zona)
    if not sistemas:
        return 0.0
    complemento = 1.0
    for s in sistemas:
        complemento *= 1.0 - p_c_do_sistema(s, linhas)
    return 1.0 - complemento


# =============================================================================
# S2 — descarga próximo da estrutura
# =============================================================================
def p_ms_do_sistema(zona: ZonaEstudo, sistema: SistemaInterno) -> float:
    """Eq. (B.4) — P_MS = (K_S1 × K_S2 × K_S3 × K_S4)².

    B.4.11: com interface isolante óptica, P_MS = 0.
    """
    if sistema.interface_optica:
        return 0.0
    return (zona.k_s1() * zona.k_s2() * sistema.k_s3 * sistema.k_s4) ** 2


def p_m_do_sistema(zona: ZonaEstudo, sistema: SistemaInterno) -> float:
    """B.4.8 a B.4.10.

    Sem DPS coordenado, P_M = P_MS (o que a Tabela B.3 já entrega com
    P_SPD = 1). Com DPS coordenado, eq. (B.3): P_M = P_SPD × P_MS.
    B.4.10: equipamento que não atende às normas de produto quanto a U_W ⇒ 1.
    """
    if not sistema.atende_normas_de_produto:
        return 1.0
    return sistema.p_spd * p_ms_do_sistema(zona, sistema)


def p_m(zona: ZonaEstudo) -> float:
    """Eq. (13) — P_M = 1 − Π(1 − P_Mi) sobre os sistemas internos da zona."""
    sistemas = _sistemas(zona)
    if not sistemas:
        return 0.0
    complemento = 1.0
    for s in sistemas:
        complemento *= 1.0 - p_m_do_sistema(zona, s)
    return 1.0 - complemento


# =============================================================================
# S3 e S4 — descarga na linha e próximo da linha
# =============================================================================
def _uw_mais_desfavoravel(zona: ZonaEstudo) -> float:
    """B.4.15 / 6.9.1.2 a) — adota-se o MENOR U_W entre os equipamentos, que é
    o que produz o maior P_LD e o maior P_LI."""
    sistemas = _sistemas(zona)
    if not sistemas:
        return UW_FALLBACK_KV
    return min(s.uw_kv for s in sistemas)


def p_ld(zona: ZonaEstudo, linha: LinhaEletrica) -> float:
    """Tabela B.8, no pior U_W da zona."""
    return T.valor_p_ld(linha.faixa_p_ld, _uw_mais_desfavoravel(zona))


def p_li(zona: ZonaEstudo, linha: LinhaEletrica) -> float:
    """Tabela B.9, no pior U_W da zona."""
    return T.valor_p_li(linha.tipo, _uw_mais_desfavoravel(zona))


def p_u(projeto: Projeto, zona: ZonaEstudo, linha: LinhaEletrica) -> float:
    """Eq. (B.8) — P_U = P_TU × P_EB × P_LD × C_LD."""
    c_ld, _ = linha.c_ld_c_li()
    return zona.p_tu * projeto.p_eb * p_ld(zona, linha) * c_ld


def p_v(projeto: Projeto, zona: ZonaEstudo, linha: LinhaEletrica) -> float:
    """Eq. (B.9) — P_V = P_EB × P_LD × C_LD."""
    c_ld, _ = linha.c_ld_c_li()
    return projeto.p_eb * p_ld(zona, linha) * c_ld


def p_w(zona: ZonaEstudo, linha: LinhaEletrica) -> float:
    """Eq. (B.10) — P_W = P_SPD × P_LD × C_LD.

    6.9.1.2 a): um valor por zona, o maior aplicável. O máximo é tomado sobre o
    PRODUTO P_SPD × P_LD de cada sistema interno, não sobre os fatores isolados.
    """
    c_ld, _ = linha.c_ld_c_li()
    sistemas = _sistemas(zona)
    if not sistemas:
        return T.valor_p_ld(linha.faixa_p_ld, UW_FALLBACK_KV) * c_ld
    pior = max(
        s.p_spd * T.valor_p_ld(linha.faixa_p_ld, s.uw_kv) for s in sistemas
    )
    return pior * c_ld


def p_z(zona: ZonaEstudo, linha: LinhaEletrica) -> float:
    """Eq. (B.11) — P_Z = P_SPD × P_LI × C_LI."""
    _, c_li = linha.c_ld_c_li()
    sistemas = _sistemas(zona)
    if not sistemas:
        return T.valor_p_li(linha.tipo, UW_FALLBACK_KV) * c_li
    pior = max(
        s.p_spd * T.valor_p_li(linha.tipo, s.uw_kv) for s in sistemas
    )
    return pior * c_li
