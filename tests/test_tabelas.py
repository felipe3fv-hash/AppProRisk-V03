"""Cobertura célula a célula das tabelas normativas.

Os valores esperados neste arquivo foram transcritos DIRETAMENTE do texto da
ABNT NBR 5419-2:2026 e são a fonte da verdade. Se um teste falhar, o errado é o
motor — nunca o teste. Alterar um valor esperado aqui exige citar a cláusula.
"""

import pytest

from spda import tabelas as T


# =============================================================================
# Anexo A
# =============================================================================
@pytest.mark.parametrize("chave,esperado", [
    ("cercada_objetos_mais_altos", 0.25),
    ("cercada_mesma_altura", 0.5),
    ("isolada", 1.0),
    ("topo_de_colina", 2.0),
])
def test_tabela_a1_c_d(chave, esperado):
    assert T.valor(T.C_D, chave) == esperado


@pytest.mark.parametrize("chave,esperado", [
    ("aereo", 1.0), ("enterrado", 0.5), ("enterrado_em_malha", 0.01),
])
def test_tabela_a2_c_i(chave, esperado):
    assert T.valor(T.C_I, chave) == esperado


@pytest.mark.parametrize("chave,esperado", [("bt_ou_sinal", 1.0), ("at_com_trafo", 0.2)])
def test_tabela_a3_c_t(chave, esperado):
    assert T.valor(T.C_T, chave) == esperado


@pytest.mark.parametrize("chave,esperado", [
    ("rural", 1.0), ("suburbano", 0.5), ("urbano", 0.1), ("urbano_acima_20m", 0.01),
])
def test_tabela_a4_c_e(chave, esperado):
    assert T.valor(T.C_E, chave) == esperado


# =============================================================================
# Anexo B
# =============================================================================
@pytest.mark.parametrize("chave,esperado", [
    ("nenhuma", 1.0), ("avisos_alerta", 1e-1), ("isolacao_eletrica", 1e-2),
    ("malha_equipotencial_solo", 1e-2), ("estrutura_metalica_continua", 1e-3),
    ("restricoes_fisicas", 0.0),
])
def test_tabela_b1_p_ta(chave, esperado):
    assert T.valor(T.P_TA, chave) == esperado


@pytest.mark.parametrize("chave,esperado", [
    ("nenhum", 1.0), ("IV", 0.2), ("III", 0.1), ("II", 0.05), ("I", 0.02),
    ("captacao_NPI_descida_natural", 0.01),
    ("cobertura_metalica_descida_natural", 0.001),
])
def test_tabela_b2_p_b(chave, esperado):
    assert T.valor(T.P_B, chave) == esperado


@pytest.mark.parametrize("chave,esperado", [
    ("nenhum", 1.0), ("III-IV", 0.05), ("II", 0.02), ("I", 0.01),
])
def test_tabela_b3_p_spd(chave, esperado):
    assert T.valor(T.P_SPD, chave) == esperado


def test_tabela_b3_melhor_que_nivel_i_e_conservador():
    # Faixa 0,005 a 0,001: adota-se o extremo conservador.
    assert T.valor(T.P_SPD, "melhor_que_I") == 0.005


@pytest.mark.parametrize("chave,esperado", [
    ("sem_dps_classe_I", 1.0), ("III-IV", 0.05), ("II", 0.02), ("I", 0.01),
])
def test_tabela_b7_p_eb(chave, esperado):
    assert T.valor(T.P_EB, chave) == esperado


@pytest.mark.parametrize("chave,esperado", [
    ("nenhuma", 1.0), ("avisos_alerta", 1e-1),
    ("isolacao_eletrica", 1e-2), ("restricoes_fisicas", 0.0),
])
def test_tabela_b6_p_tu(chave, esperado):
    assert T.valor(T.P_TU, chave) == esperado


@pytest.mark.parametrize("chave,esperado", [
    ("nao_blindado_sem_roteamento", 1.0),
    ("nao_blindado_evita_grandes_lacos", 0.5),
    ("nao_blindado_evita_lacos_medios", 0.2),
    ("nao_blindado_evita_pequenos_lacos", 0.01),
    ("blindado_ou_conduto_metalico", 0.0001),
])
def test_tabela_b5_k_s3(chave, esperado):
    assert T.valor(T.K_S3, chave) == esperado


# --- Tabela B.8 — todas as 28 células ---------------------------------------
TABELA_B8 = {
    "nao_creditada": {0.35: 1, 0.5: 1, 1: 1, 1.5: 1, 2.5: 1, 4: 1, 6: 1},
    "rs_5_a_20":     {0.35: 1, 0.5: 1, 1: 1, 1.5: 1, 2.5: 0.95, 4: 0.9, 6: 0.8},
    "rs_1_a_5":      {0.35: 1, 0.5: 1, 1: 0.9, 1.5: 0.8, 2.5: 0.6, 4: 0.3, 6: 0.1},
    "rs_ate_1":      {0.35: 1, 0.5: 0.85, 1: 0.6, 1.5: 0.4, 2.5: 0.2, 4: 0.04, 6: 0.02},
}


@pytest.mark.parametrize("faixa", sorted(TABELA_B8))
@pytest.mark.parametrize("uw", [0.35, 0.5, 1, 1.5, 2.5, 4, 6])
def test_tabela_b8_p_ld_celula_a_celula(faixa, uw):
    assert T.valor_p_ld(faixa, uw) == pytest.approx(TABELA_B8[faixa][uw])


@pytest.mark.parametrize("r_s,faixa", [
    (0.1, "rs_ate_1"), (1.0, "rs_ate_1"),
    (1.01, "rs_1_a_5"), (5.0, "rs_1_a_5"),
    (5.01, "rs_5_a_20"), (20.0, "rs_5_a_20"),
    (20.01, "nao_creditada"), (100.0, "nao_creditada"),
])
def test_faixas_de_resistencia_de_blindagem(r_s, faixa):
    assert T.faixa_rs(r_s) == faixa


@pytest.mark.parametrize("uw,esperado", [
    (0.2, 1.0),   # abaixo da 1ª coluna → usa 0,35 kV (pior caso, P_LD = 1)
    (0.9, 0.85),  # entre 0,5 e 1 → arredonda para baixo (conservador)
    (3.9, 0.2),   # entre 2,5 e 4 → coluna de 2,5
    (10.0, 0.02), # acima da última → coluna de 6
])
def test_p_ld_interpola_para_baixo_conservador(uw, esperado):
    assert T.valor_p_ld("rs_ate_1", uw) == pytest.approx(esperado)


# --- Tabela B.9 — todas as 10 células ---------------------------------------
TABELA_B9 = {
    "energia": {1: 1, 1.5: 0.6, 2.5: 0.3, 4: 0.16, 6: 0.1},
    "sinal":   {1: 1, 1.5: 0.5, 2.5: 0.2, 4: 0.08, 6: 0.04},
}


@pytest.mark.parametrize("tipo", sorted(TABELA_B9))
@pytest.mark.parametrize("uw", [1, 1.5, 2.5, 4, 6])
def test_tabela_b9_p_li_celula_a_celula(tipo, uw):
    assert T.valor_p_li(tipo, uw) == pytest.approx(TABELA_B9[tipo][uw])


# --- Tabela B.4 — todas as linhas -------------------------------------------
@pytest.mark.parametrize("kwargs,esperado,descricao", [
    ({}, (1.0, 1.0), "aérea não blindada, sem ligação equipotencial"),
    ({"instalacao_subterranea": True}, (1.0, 1.0), "subterrânea não blindada"),
    ({"neutro_multiaterrado": True}, (1.0, 0.2), "energia com neutro multiaterrado"),
    ({"blindada": True, "instalacao_subterranea": True}, (1.0, 0.3),
     "subterrânea blindada, blindagem fora do BEP"),
    ({"blindada": True}, (1.0, 0.1), "aérea blindada, blindagem fora do BEP"),
    ({"blindada": True, "blindagem_no_mesmo_bep": True}, (1.0, 0.0),
     "blindada com blindagem no mesmo BEP"),
    ({"cabo_protecao_ou_conduto_metalico": True, "blindagem_no_mesmo_bep": True},
     (0.0, 0.0), "eletroduto/cabo de proteção metálico no mesmo BEP"),
    ({"sem_linha_externa": True}, (0.0, 0.0), "sem linha externa / fibra óptica"),
    ({"interface_isolante": True, "interface_isolante_protegida_por_dps": True},
     (0.0, 0.0), "interface isolante protegida por DPS"),
    ({"interface_isolante": True}, (1.0, 0.0),
     "interface isolante SEM DPS — nota a: C_LD = 1"),
])
def test_tabela_b4_c_ld_c_li(kwargs, esperado, descricao):
    assert T.valor_c_ld_c_li(**kwargs) == esperado, descricao


def test_neutro_multiaterrado_nao_e_inferido_de_linha_bt():
    """Regressão do achado B-06: ser BT não implica neutro multiaterrado."""
    assert T.valor_c_ld_c_li() == (1.0, 1.0)


# =============================================================================
# Anexo C
# =============================================================================
@pytest.mark.parametrize("chave,esperado", [
    ("terra_concreto", 1e-2), ("marmore_ceramica", 1e-3),
    ("brita_tapete_carpete", 1e-4), ("asfalto_linoleo_madeira", 1e-5),
])
def test_tabela_c3_r_t(chave, esperado):
    assert T.valor(T.R_T, chave) == esperado


@pytest.mark.parametrize("chave,esperado", [
    ("nenhuma", 1.0), ("manual", 0.5), ("automatica", 0.2),
])
def test_tabela_c4_r_p(chave, esperado):
    assert T.valor(T.R_P, chave) == esperado


@pytest.mark.parametrize("chave,esperado", [
    ("explosao_zonas_0_20", 1.0), ("explosao_zonas_1_21", 1e-1),
    ("explosao_zonas_2_22", 1e-3), ("incendio_alto", 1e-1),
    ("incendio_normal", 1e-2), ("incendio_baixo", 1e-3), ("nenhum", 0.0),
])
def test_tabela_c5_r_f(chave, esperado):
    assert T.valor(T.R_F, chave) == esperado


@pytest.mark.parametrize("chave,esperado", [
    ("sem_perigo", 1.0), ("panico_baixo", 2.0), ("panico_medio", 5.0),
    ("dificuldade_evacuacao", 5.0), ("panico_alto", 10.0),
])
def test_tabela_c6_h_z(chave, esperado):
    assert T.valor(T.H_Z, chave) == esperado


def test_tabela_c6_inclui_alto_panico():
    """Regressão do achado G-01: h_z = 10 precisa existir."""
    assert 10.0 in {v for v, _ in T.H_Z.values()}


@pytest.mark.parametrize("chave,esperado", [("robusta", 1.0), ("simples", 2.0)])
def test_tabela_c7_r_s(chave, esperado):
    assert T.valor(T.R_S_CONSTRUCAO, chave) == esperado


def test_tabela_c9_l_f_l3():
    assert T.L_F_L3 == 1e-1


# --- Tabela C.2 e Tabela D.2 são conjuntos DISTINTOS -------------------------
@pytest.mark.parametrize("ocupacao,lf_l1,lf_l4", [
    ("explosao", 1e-1, 1.0),
    ("hospital_uti", 1e-1, 0.5),
    ("industrial", 2e-2, 0.5),
    ("comercial", 2e-2, 0.2),
    ("museu", 5e-2, 0.5),
    ("igreja", 5e-2, 0.2),
    ("escola", 1e-1, 0.2),
    ("outros", 1e-2, 0.1),
])
def test_l_f_de_l1_e_de_l4_nao_se_confundem(ocupacao, lf_l1, lf_l4):
    """Regressão do achado B-02, o mais grave da versão anterior."""
    p = T.perdas_da_ocupacao(ocupacao)
    assert p["L_F_L1"] == pytest.approx(lf_l1), "Tabela C.2"
    assert p["L_F_L4"] == pytest.approx(lf_l4), "Tabela D.2"


@pytest.mark.parametrize("ocupacao,lo_l1,lo_l4", [
    ("explosao", 1e-1, 1e-1),
    ("hospital_uti", 1e-2, 1e-2),
    ("hospital_outras", 1e-3, 1e-2),
    ("comercial", 0.0, 1e-2),
    ("museu", 0.0, 1e-3),
    ("outros", 0.0, 1e-4),
])
def test_l_o_de_l1_e_de_l4_nao_se_confundem(ocupacao, lo_l1, lo_l4):
    p = T.perdas_da_ocupacao(ocupacao)
    assert p["L_O_L1"] == pytest.approx(lo_l1), "Tabela C.2"
    assert p["L_O_L4"] == pytest.approx(lo_l4), "Tabela D.2"


def test_l_o_de_l1_e_positivo_apenas_onde_a_tabela_c2_define():
    """A Tabela C.2 só define L_O para explosão e hospitais — coerente com a
    nota `a` da Tabela 2, que restringe R_C1/R_M1/R_W1/R_Z1 a esses casos."""
    com_lo = {k for k in T.OCUPACOES if T.perdas_da_ocupacao(k)["L_O_L1"] > 0}
    assert com_lo == {"explosao", "hospital_uti", "hospital_outras"}


def test_l_t_unico_para_todos_os_tipos():
    assert T.L_T_L1 == 1e-2 and T.L_T_L4 == 1e-2


# =============================================================================
# Limites
# =============================================================================
def test_riscos_toleraveis_tabela_4():
    assert T.R_T_R1 == 1e-5
    assert T.R_T_R3 == 1e-4


def test_frequencia_toleravel_7_3_4():
    assert T.F_T_CRITICO == 0.1
    assert T.F_T_NAO_CRITICO == 1.0


def test_risco_toleravel_r4_d_1_2():
    assert T.R_T_R4 == 1e-3


def test_chaves_de_explosao():
    assert T.RF_COM_RISCO_EXPLOSAO == {
        "explosao_zonas_0_20", "explosao_zonas_1_21", "explosao_zonas_2_22",
    }
