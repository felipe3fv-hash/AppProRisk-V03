"""Anexos C e D — quantidade de perda L_X, separada por tipo de perda.

A correção estrutural em relação à versão anterior: L_F e L_O NÃO são um número
só. A norma usa três conjuntos diferentes para o mesmo edifício —

    Tabela C.2  →  L1  (perda de vida humana)
    Tabela C.9  →  L3  (perda de patrimônio cultural)
    Tabela D.2  →  L4  (perda de valor econômico)

— e a versão anterior alimentava os três com os valores da Tabela D.2.
Aqui os três vêm da mesma escolha de ocupação (`tabelas.OCUPACOES`), que
preenche cada tabela com o valor que lhe corresponde.
"""

from __future__ import annotations

from .modelo import Projeto, ZonaEstudo


# =============================================================================
# L1 — perda de vida humana (Tabela C.1)
# =============================================================================
def fator_presenca(projeto: Projeto, zona: ZonaEstudo) -> float:
    """(n_z / n_t) × (t_z / 8 760), com t_z limitado a 8 760 h/ano (C.3.1 c)."""
    n_t = max(projeto.pessoas_total, 1.0)
    t_z = min(max(zona.horas_presenca_ano, 0.0), 8760.0)
    return (zona.pessoas_na_zona / n_t) * (t_z / 8760.0)


def l_a1(projeto: Projeto, zona: ZonaEstudo) -> float:
    """Eq. (C.1) — L_A = r_t × L_T × n_z/n_t × t_z/8760 × r_s."""
    return zona.r_t * zona.perdas["L_T_L1"] * fator_presenca(projeto, zona) * zona.r_s


def l_u1(projeto: Projeto, zona: ZonaEstudo) -> float:
    """Eq. (C.2) — L_U = L_A."""
    return l_a1(projeto, zona)


def l_b1(projeto: Projeto, zona: ZonaEstudo) -> float:
    """Eq. (C.3) — L_B = r_p × r_f × h_z × L_FT × n_z/n_t × t_z/8760 × r_s.

    C.3.2: havendo perda ambiental, L_FT = L_F + L_E substitui L_F.
    """
    l_ft = zona.perdas["L_F_L1"] + projeto.l_e_para_l1()
    return (
        zona.r_p * zona.r_f * zona.h_z * l_ft
        * fator_presenca(projeto, zona) * zona.r_s
    )


def l_v1(projeto: Projeto, zona: ZonaEstudo) -> float:
    """Eq. (C.3) — L_V = L_B."""
    return l_b1(projeto, zona)


def l_c1(projeto: Projeto, zona: ZonaEstudo) -> float:
    """Eq. (C.4) — L_C = L_M = L_W = L_Z = L_O × n_z/n_t × t_z/8760 × r_s."""
    return zona.perdas["L_O_L1"] * fator_presenca(projeto, zona) * zona.r_s


l_m1 = l_w1 = l_z1 = l_c1


# =============================================================================
# L3 — perda de patrimônio cultural (Tabela C.8)
# =============================================================================
def l_b3(projeto: Projeto, zona: ZonaEstudo) -> float:
    """Eq. (C.7) — L_B = L_V = r_p × r_f × L_F × c_z / c_t."""
    c_t = projeto.valor_total_estrutura
    if c_t <= 0:
        return 0.0
    return zona.r_p * zona.r_f * zona.perdas["L_F_L3"] * (
        zona.valor_patrimonio_cultural / c_t
    )


l_v3 = l_b3


def zona_tem_patrimonio(zona: ZonaEstudo) -> bool:
    return zona.valor_patrimonio_cultural > 0.0


# =============================================================================
# L4 — perda de valor econômico (Tabela D.1)
# =============================================================================
def _razao(projeto: Projeto, numerador: float) -> float:
    """Nota `a` da Tabela D.1.

    As razões c_x/c_t só valem na avaliação detalhada do Anexo D. Quando se adota
    o valor representativo de R_T para R4 (D.1.2), as razões devem ser
    substituídas por 1. São dois modos mutuamente exclusivos.
    """
    if projeto.modo_r4 == "representativo":
        return 1.0
    c_t = projeto.valor_total_estrutura
    if c_t <= 0:
        return 0.0
    return numerador / c_t


def l_a4(projeto: Projeto, zona: ZonaEstudo) -> float:
    """Eq. (D.1) — L_A = r_t × L_T × c_a / c_t (só onde houver animais)."""
    return zona.r_t * zona.perdas["L_T_L4"] * _razao(projeto, zona.valor_animais)


l_u4 = l_a4


def l_b4(projeto: Projeto, zona: ZonaEstudo) -> float:
    """Eq. (D.3) — L_B = L_V = r_p × r_f × L_FT × (c_a+c_b+c_c+c_s)/c_t."""
    bens = (
        zona.valor_animais + zona.valor_edificacao
        + zona.valor_conteudo + zona.valor_sistemas
    )
    l_ft = zona.perdas["L_F_L4"] + projeto.l_e_para_l4()
    return zona.r_p * zona.r_f * l_ft * _razao(projeto, bens)


l_v4 = l_b4


def l_c4(projeto: Projeto, zona: ZonaEstudo) -> float:
    """Eq. (D.4) — L_C = L_M = L_W = L_Z = L_O × c_s / c_t."""
    return zona.perdas["L_O_L4"] * _razao(projeto, zona.valor_sistemas)


l_m4 = l_w4 = l_z4 = l_c4
