"""Casos de referência calculados à mão e congelados.

Estes números NÃO foram produzidos pelo motor: foram calculados manualmente a
partir das equações da norma e conferidos termo a termo. Servem para detectar
qualquer alteração de comportamento do motor em futuras versões.

Se um destes testes falhar, ou o motor regrediu, ou o cálculo manual precisa ser
refeito e documentado. Nunca ajuste o valor esperado sem refazer a conta.
"""

import math

import pytest

from spda import analise
from spda.modelo import (
    Estrutura,
    LinhaEletrica,
    Projeto,
    SistemaInterno,
    Trecho,
    ZonaEstudo,
)

TOL = 1e-9


# =============================================================================
# CASO 1 — galpão comercial, uma zona, uma linha BT aérea, sem proteção alguma
# =============================================================================
# Geometria: L = 40 m, W = 20 m, H = 10 m, C_D = 0,5
#   A_D = 40×20 + 2×30×(40+20) + π×30²  = 800 + 3 600 + 2 827,433388 = 7 227,433388 m²
#   N_D = 6 × 7 227,433388 × 0,5 × 1e-6                       = 2,16823002e-02
#   A_M = 2×500×60 + π×500²             = 60 000 + 785 398,163 = 845 398,163 m²
#   N_M = 6 × 845 398,163 × 1e-6                              = 5,07238898
# Linha: 1 trecho de 500 m, aéreo (C_I=1), suburbano (C_E=0,5), BT (C_T=1)
#   A_L = 40×500 = 20 000 → N_L = 6×20 000×1×0,5×1×1e-6       = 0,06
#   A_I = 4 000×500 = 2e6 → N_I = 6×2e6×1×0,5×1×1e-6          = 6,00
#   N_DJ = 0 (sem estrutura adjacente)
# Probabilidades (P_B=1, P_EB=1, P_TA=1, P_TU=1, P_SPD=1, U_W=2,5 kV, não blindada):
#   P_A = 1×1 = 1 · P_B = 1
#   C_LD = C_LI = 1 (Tabela B.4, "nenhuma ou indefinida")
#   P_C = 1 − (1 − 1×1) = 1
#   P_MS = (1×1×1×1/2,5)² = 0,16 → P_M = 1×0,16 = 0,16
#   P_LD = 1 (blindagem não creditada) → P_U = P_V = P_W = 1
#   P_LI(energia; 2,5 kV) = 0,3 → P_Z = 1×0,3×1 = 0,3
# Perdas (ocupação comercial: L_F = 2e-2, L_O = 0; r_t=1e-2, r_p=1, r_f=1e-2,
#         h_z=1, r_s=1, n_z/n_t=1, t_z/8760=1):
#   L_A1 = L_U1 = 1e-2 × 1e-2 = 1e-4
#   L_B1 = L_V1 = 1 × 1e-2 × 1 × 2e-2 = 2e-4
# Componentes:
#   R_A = 2,16823002e-02 × 1 × 1e-4 = 2,16823002e-06
#   R_B = 2,16823002e-02 × 1 × 2e-4 = 4,33646003e-06
#   R_U = 0,06 × 1 × 1e-4           = 6,00000000e-06
#   R_V = 0,06 × 1 × 2e-4           = 1,20000000e-05
#   R_C = R_M = R_W = R_Z = 0 (nota a da Tabela 2 não se aplica a comercial)
#   R1  = 2,45046900e-05  →  R1 > R_T = 1e-5, a estrutura NÃO atende
# Frequência (Tabela 7):
#   F_B = 0 (sem equipamento em ZPR0A)
#   F_C = N_D × P_C = 2,16823002e-02
#   F_M = N_M × P_M = 5,07238898 × 0,16 = 0,811582237
#   F_V = 0,06 × P_EB = 0,06 · F_W = 0,06 × 1 = 0,06
#   F_Z = 6,0 × 0,3 = 1,80
#   F   = 2,75326232
# -----------------------------------------------------------------------------
A_D_CASO1 = 800 + 2 * 30 * 60 + math.pi * 30**2
A_M_CASO1 = 2 * 500 * 60 + math.pi * 500**2
N_D_CASO1 = 6 * A_D_CASO1 * 0.5 * 1e-6
N_M_CASO1 = 6 * A_M_CASO1 * 1e-6

CASO1 = {
    "N_D": N_D_CASO1,
    "N_M": N_M_CASO1,
    "N_L": 0.06,
    "N_I": 6.0,
    "R_A": N_D_CASO1 * 1e-4,
    "R_B": N_D_CASO1 * 2e-4,
    "R_U": 6.0e-6,
    "R_V": 1.2e-5,
    "R1": N_D_CASO1 * 1e-4 + N_D_CASO1 * 2e-4 + 6.0e-6 + 1.2e-5,
    "F_C": N_D_CASO1 * 1.0,
    "F_M": N_M_CASO1 * 0.16,
    "F_V": 0.06,
    "F_W": 0.06,
    "F_Z": 1.8,
}
CASO1["F"] = CASO1["F_C"] + CASO1["F_M"] + CASO1["F_V"] + CASO1["F_W"] + CASO1["F_Z"]


def projeto_caso1() -> Projeto:
    return Projeto(
        municipio="Petrolina", uf="PE", n_g=6.0, pessoas_total=20.0,
        p_b_chave="nenhum", p_eb_chave="sem_dps_classe_I",
        estrutura=Estrutura(comprimento_m=40, largura_m=20, altura_m=10,
                            c_d_chave="cercada_mesma_altura"),
        linhas=[LinhaEletrica(
            id_linha="L1", tipo="energia",
            trechos=[Trecho(id_trecho="T1", comprimento_m=500, c_i_chave="aereo",
                            c_e_chave="suburbano", c_t_chave="bt_ou_sinal")],
        )],
        zonas=[ZonaEstudo(
            id_zona="Z1", ocupacao="comercial",
            pessoas_na_zona=20.0, horas_presenca_ano=8760.0,
            r_t_chave="terra_concreto", r_p_chave="nenhuma",
            r_f_chave="incendio_normal", h_z_chave="sem_perigo", r_s_chave="robusta",
            sistemas_internos=[SistemaInterno(
                id_sistema="Quadro geral", uw_kv=2.5, blindado=False,
                p_spd_chave="nenhum", k_s3_chave="nao_blindado_sem_roteamento",
                ids_linhas=["L1"],
            )],
        )],
    )


@pytest.fixture(scope="module")
def r1_caso1():
    return analise.analisar(projeto_caso1())


@pytest.mark.parametrize("grandeza", ["N_D", "N_M"])
def test_caso1_eventos_na_estrutura(r1_caso1, grandeza):
    obtido = r1_caso1.n_d if grandeza == "N_D" else r1_caso1.n_m
    assert obtido == pytest.approx(CASO1[grandeza], rel=TOL)


def test_caso1_eventos_na_linha(r1_caso1):
    ev = r1_caso1.eventos_linhas["L1"]
    assert ev.n_l == pytest.approx(CASO1["N_L"], rel=TOL)
    assert ev.n_i == pytest.approx(CASO1["N_I"], rel=TOL)
    assert ev.n_dj == 0.0


@pytest.mark.parametrize("componente", ["R_A", "R_B", "R_U", "R_V"])
def test_caso1_componentes_de_r1(r1_caso1, componente):
    assert r1_caso1.componentes_r1()[componente] == pytest.approx(CASO1[componente], rel=TOL)


@pytest.mark.parametrize("componente", ["R_C", "R_M", "R_W", "R_Z"])
def test_caso1_componentes_de_falha_sao_nulos(r1_caso1, componente):
    assert r1_caso1.componentes_r1()[componente] == 0.0


def test_caso1_r1_total(r1_caso1):
    assert r1_caso1.r1 == pytest.approx(CASO1["R1"], rel=TOL)


def test_caso1_r1_nao_atende_o_risco_toleravel(r1_caso1):
    assert not r1_caso1.r1_aprovado           # 2,4505e-05 > 1e-05


@pytest.mark.parametrize("componente", ["F_C", "F_M", "F_V", "F_W", "F_Z"])
def test_caso1_componentes_de_f(r1_caso1, componente):
    assert r1_caso1.componentes_f()[componente] == pytest.approx(CASO1[componente], rel=TOL)


def test_caso1_f_b_nulo(r1_caso1):
    assert r1_caso1.componentes_f()["F_B"] == 0.0


def test_caso1_f_total(r1_caso1):
    assert r1_caso1.f == pytest.approx(CASO1["F"], rel=TOL)


def test_caso1_f_nao_atende_em_nenhum_dos_dois_limites(r1_caso1):
    assert r1_caso1.f > 1.0    # reprova mesmo como sistema não crítico


# =============================================================================
# CASO 2 — o mesmo galpão, agora protegido. Verifica a direção e a MAGNITUDE
#          da redução obtida por cada medida.
# =============================================================================
# SPDA nível I           → P_B = 0,02
# Avisos + isolação      → P_TA = 0,1 × 0,01 = 1e-3
# DPS classe I nível I   → P_EB = 0,01
# Linha blindada R_S = 1 Ω/km interligada ao mesmo BEP, U_W = 6 kV
#                        → P_LD = 0,02 e C_LI = 0
# DPS coordenado nível I → P_SPD = 0,01
#
#   R_A = N_D × (1e-3 × 0,02) × 1e-4 = N_D × 2e-9
#   R_B = N_D × 0,02 × 2e-4          = N_D × 4e-6
#   P_U = P_TU × P_EB × P_LD × C_LD = 1 × 0,01 × 0,02 × 1 = 2e-4
#   R_U = 0,06 × 2e-4 × 1e-4 = 1,2e-9
#   P_V = 0,01 × 0,02 × 1 = 2e-4  → R_V = 0,06 × 2e-4 × 2e-4 = 2,4e-9
#   P_Z = P_SPD × P_LI × C_LI = 0,01 × 0,1 × 0 = 0 → R_Z = 0 e F_Z = 0
def projeto_caso2() -> Projeto:
    p = projeto_caso1()
    p.p_b_chave = "I"
    p.p_eb_chave = "I"
    z = p.zonas[0]
    z.p_ta_chaves = ["avisos_alerta", "isolacao_eletrica"]
    ln = p.linhas[0]
    ln.blindada = True
    ln.blindagem_no_mesmo_bep = True
    ln.resistencia_blindagem_ohm_km = 1.0
    s = z.sistemas_internos[0]
    s.uw_kv = 6.0
    s.p_spd_chave = "I"
    s.blindado = True
    return p


@pytest.fixture(scope="module")
def r2_caso2():
    return analise.analisar(projeto_caso2())


def test_caso2_r_a_com_medidas(r2_caso2):
    assert r2_caso2.componentes_r1()["R_A"] == pytest.approx(N_D_CASO1 * 2e-9, rel=TOL)


def test_caso2_r_b_com_spda_nivel_i(r2_caso2):
    assert r2_caso2.componentes_r1()["R_B"] == pytest.approx(N_D_CASO1 * 4e-6, rel=TOL)


def test_caso2_r_u_e_r_v_com_blindagem_e_dps(r2_caso2):
    c = r2_caso2.componentes_r1()
    assert c["R_U"] == pytest.approx(0.06 * 2e-4 * 1e-4, rel=TOL)
    assert c["R_V"] == pytest.approx(0.06 * 2e-4 * 2e-4, rel=TOL)


def test_caso2_c_li_zerado_anula_f_z(r2_caso2):
    assert r2_caso2.componentes_f()["F_Z"] == 0.0


def test_caso2_r1_passa_a_atender(r2_caso2):
    assert r2_caso2.r1_aprovado


def test_caso2_reducao_de_r1_em_duas_ordens_de_grandeza(r1_caso1, r2_caso2):
    # Redução medida: 2,4505e-05 → 9,0373e-08, fator ≈ 271×.
    assert r2_caso2.r1 < r1_caso1.r1 / 100


# =============================================================================
# CASO 3 — estrutura com risco de explosão: as regras condicionais da norma
# =============================================================================
def projeto_caso3() -> Projeto:
    p = projeto_caso1()
    z = p.zonas[0]
    z.ocupacao = "explosao"
    z.r_f_chave = "explosao_zonas_0_20"
    z.r_p_chave = "automatica"        # C.3.4 deve sobrepor para 1,0
    return p


def test_caso3_r_p_forcado_a_um_por_c_3_4():
    assert projeto_caso3().zonas[0].r_p == 1.0


def test_caso3_componentes_de_falha_entram_em_r1():
    r = analise.analisar(projeto_caso3())
    assert r.inclui_falha_sistemas_em_r1
    c = r.componentes_r1()
    assert c["R_C"] > 0 and c["R_M"] > 0 and c["R_W"] > 0 and c["R_Z"] > 0


def test_caso3_l_b1_usa_l_f_da_tabela_c2_para_explosao():
    """L_F(L1) = 1e-1 pela Tabela C.2 — e não 1,0, que é o valor da Tabela D.2."""
    r = analise.analisar(projeto_caso3())
    esperado = N_D_CASO1 * 1.0 * (1.0 * 1.0 * 1.0 * 1e-1 * 1.0 * 1.0)
    assert r.componentes_r1()["R_B"] == pytest.approx(esperado, rel=TOL)
