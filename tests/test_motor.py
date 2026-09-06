"""Testes do motor: Anexo A, composição de probabilidades, perdas e regras
condicionais da norma. Inclui a regressão de cada achado bloqueante e grave da
auditoria da versão 1.
"""

import math

import pytest

from spda import analise, eventos, ng, perdas, probabilidades, tabelas as T
from spda.modelo import (
    Estrutura,
    EstruturaAdjacente,
    LinhaEletrica,
    Projeto,
    SistemaInterno,
    Trecho,
    ZonaEstudo,
)
from spda.projeto_io import clonar, de_json, impressao_digital, para_json
from spda.validacao import erros, tem_erro, validar


# =============================================================================
# Anexo A
# =============================================================================
def test_a1_area_de_exposicao_retangular():
    """Eq. (A.1) conferida à mão: L=40, W=20, H=10."""
    est = Estrutura(comprimento_m=40, largura_m=20, altura_m=10)
    esperado = 40 * 20 + 2 * 30 * 60 + math.pi * 30**2
    assert est.a_d() == pytest.approx(esperado)


def test_a2_saliencia_prevalece_quando_maior():
    """A.2.1.3.2 — adota-se o MAIOR entre A_D(H_mín) e π(3·H_P)²."""
    est = Estrutura(comprimento_m=5, largura_m=5, altura_m=3, altura_saliencia_m=40)
    assert est.a_d() == pytest.approx(math.pi * (3 * 40) ** 2)


def test_a2_saliencia_menor_nao_reduz_a_d():
    base = Estrutura(comprimento_m=40, largura_m=20, altura_m=10)
    com = Estrutura(comprimento_m=40, largura_m=20, altura_m=10, altura_saliencia_m=2)
    assert com.a_d() == pytest.approx(base.a_d())


def test_a_d_informada_graficamente_prevalece():
    est = Estrutura(comprimento_m=40, largura_m=20, altura_m=10,
                    a_d_informada_m2=1234.5, a_d_justificativa="método gráfico")
    assert est.a_d() == 1234.5


def test_a6_area_am():
    est = Estrutura(comprimento_m=40, largura_m=20, altura_m=10)
    assert est.a_m() == pytest.approx(2 * 500 * 60 + math.pi * 500**2)


def test_a8_area_al_aerea():
    assert Trecho(comprimento_m=300).a_l() == pytest.approx(40 * 300)


def test_a8_area_al_enterrada_resistividade_alta():
    """Nota 1 da Tabela A.2 — ρ > 400 Ω·m ⇒ A_L = 0,6·√ρ·L_L."""
    t = Trecho(comprimento_m=300, c_i_chave="enterrado", resistividade_solo_ohm_m=1000)
    assert t.a_l() == pytest.approx(0.6 * math.sqrt(1000) * 300)


def test_a8_area_al_enterrada_resistividade_padrao():
    t = Trecho(comprimento_m=300, c_i_chave="enterrado", resistividade_solo_ohm_m=400)
    assert t.a_l() == pytest.approx(40 * 300)


def test_a10_area_ai():
    assert Trecho(comprimento_m=300).a_i() == pytest.approx(4000 * 300)


def test_a3_a5_numero_de_eventos():
    est = Estrutura(comprimento_m=40, largura_m=20, altura_m=10, c_d_chave="cercada_mesma_altura")
    assert eventos.n_d(6.0, est) == pytest.approx(6.0 * est.a_d() * 0.5 * 1e-6)
    assert eventos.n_m(6.0, est) == pytest.approx(6.0 * est.a_m() * 1e-6)


def test_a4_n_dj_com_c_t_da_linha():
    ln = LinhaEletrica(
        id_linha="L", trechos=[Trecho(c_t_chave="at_com_trafo")],
        estrutura_adjacente=EstruturaAdjacente(comprimento_m=30, largura_m=9, altura_m=5),
    )
    adj = ln.estrutura_adjacente
    assert eventos.n_dj(6.0, ln) == pytest.approx(6.0 * adj.a_dj() * adj.c_dj * 0.2 * 1e-6)


def test_n_dj_zero_sem_estrutura_adjacente():
    assert eventos.n_dj(6.0, LinhaEletrica(id_linha="L")) == 0.0


def test_n_l_soma_sobre_trechos():
    """6.4.3 — a linha dividida em trechos soma os N_L parciais."""
    inteira = LinhaEletrica(id_linha="A", trechos=[Trecho(comprimento_m=600)])
    partida = LinhaEletrica(id_linha="B", trechos=[
        Trecho(id_trecho="1", comprimento_m=200),
        Trecho(id_trecho="2", comprimento_m=400),
    ])
    assert eventos.n_l(6.0, partida) == pytest.approx(eventos.n_l(6.0, inteira))


# =============================================================================
# Anexo B — composição
# =============================================================================
def _sistema(**kw):
    base = dict(id_sistema="S1", uw_kv=2.5, blindado=False, sistema_independente=True)
    base.update(kw)
    return SistemaInterno(**base)


def test_eq12_p_c_compoe_sobre_sistemas_internos():
    """6.9.1.2 b) — P_C = 1 − Π(1 − P_Ci) sobre SISTEMAS, não sobre linhas."""
    ln = LinhaEletrica(id_linha="L1")
    linhas = {"L1": ln}
    s1 = _sistema(id_sistema="A", p_spd_chave="II", sistema_independente=False, ids_linhas=["L1"])
    s2 = _sistema(id_sistema="B", p_spd_chave="II", sistema_independente=False, ids_linhas=["L1"])
    z = ZonaEstudo(id_zona="Z", sistemas_internos=[s1, s2])
    esperado = 1 - (1 - 0.02 * 1.0) ** 2
    assert probabilidades.p_c(z, linhas) == pytest.approx(esperado)


def test_duplicar_a_linha_nao_altera_p_c():
    """Regressão do achado G-05: na versão anterior, cadastrar a mesma linha
    duas vezes aumentava P_C."""
    s = _sistema(sistema_independente=False, ids_linhas=["L1"], p_spd_chave="II")
    z = ZonaEstudo(id_zona="Z", sistemas_internos=[s])
    uma = probabilidades.p_c(z, {"L1": LinhaEletrica(id_linha="L1")})
    s2 = _sistema(sistema_independente=False, ids_linhas=["L1", "L2"], p_spd_chave="II")
    z2 = ZonaEstudo(id_zona="Z", sistemas_internos=[s2])
    duas = probabilidades.p_c(z2, {"L1": LinhaEletrica(id_linha="L1"),
                                   "L2": LinhaEletrica(id_linha="L2")})
    assert uma == pytest.approx(duas)


def test_b4_4_sistema_interno_nao_blindado_usa_c_ld_igual_a_1():
    ln = LinhaEletrica(id_linha="L1", blindada=True, blindagem_no_mesmo_bep=True,
                       cabo_protecao_ou_conduto_metalico=True)
    assert ln.c_ld_c_li() == (0.0, 0.0)
    s = _sistema(blindado=False, sistema_independente=False, ids_linhas=["L1"], p_spd_chave="nenhum")
    z = ZonaEstudo(id_zona="Z", sistemas_internos=[s])
    assert probabilidades.p_c(z, {"L1": ln}) == pytest.approx(1.0)


def test_b4_11_interface_optica_zera_p_ms():
    z = ZonaEstudo(id_zona="Z", sistemas_internos=[_sistema(interface_optica=True)])
    assert probabilidades.p_m(z) == 0.0


def test_b4_10_equipamento_fora_de_norma_forca_p_m_igual_a_1():
    z = ZonaEstudo(id_zona="Z", sistemas_internos=[_sistema(atende_normas_de_produto=False)])
    assert probabilidades.p_m(z) == pytest.approx(1.0)


def test_b4_12_k_s1_limitado_a_um_e_metade_com_malha():
    z = ZonaEstudo(id_zona="Z", largura_malha_zpr01_m=20)
    assert z.k_s1() == 1.0                       # 0,12 × 20 = 2,4 → limitado a 1
    z.largura_malha_zpr01_m = 5
    assert z.k_s1() == pytest.approx(0.6)
    z.rede_equipotencial_em_malha = True
    assert z.k_s1() == pytest.approx(0.3)
    z.blindagem_continua_zpr01 = True
    assert z.k_s1() == 1e-4


def test_b4_14_k_s4_limitado_a_um():
    assert _sistema(uw_kv=0.5).k_s4 == 1.0
    assert _sistema(uw_kv=4.0).k_s4 == pytest.approx(0.25)


def test_b2_2_p_ta_e_produto_de_multiplas_medidas():
    z = ZonaEstudo(id_zona="Z", p_ta_chaves=["avisos_alerta", "isolacao_eletrica"])
    assert z.p_ta == pytest.approx(1e-3)


def test_p_ld_usa_o_menor_uw_da_zona():
    """B.4.15 / 6.9.1.2 a) — pior caso entre os equipamentos."""
    ln = LinhaEletrica(id_linha="L", blindada=True, blindagem_no_mesmo_bep=True,
                       resistencia_blindagem_ohm_km=0.5)
    z = ZonaEstudo(id_zona="Z", sistemas_internos=[_sistema(uw_kv=6.0), _sistema(uw_kv=1.5)])
    assert probabilidades.p_ld(z, ln) == pytest.approx(0.4)   # coluna de 1,5 kV


def test_blindagem_fora_do_bep_nao_e_creditada():
    """Regressão do achado B-05."""
    ln = LinhaEletrica(id_linha="L", blindada=True, blindagem_no_mesmo_bep=False,
                       resistencia_blindagem_ohm_km=0.5)
    assert ln.faixa_p_ld == "nao_creditada"
    z = ZonaEstudo(id_zona="Z", sistemas_internos=[_sistema(uw_kv=6.0)])
    assert probabilidades.p_ld(z, ln) == 1.0


def test_blindagem_no_bep_e_creditada():
    ln = LinhaEletrica(id_linha="L", blindada=True, blindagem_no_mesmo_bep=True,
                       resistencia_blindagem_ohm_km=1.0)
    z = ZonaEstudo(id_zona="Z", sistemas_internos=[_sistema(uw_kv=6.0)])
    assert probabilidades.p_ld(z, ln) == pytest.approx(0.02)
    assert ln.c_ld_c_li() == (1.0, 0.0)


# =============================================================================
# Anexos C e D — perdas
# =============================================================================
def _projeto_minimo(**kw):
    p = Projeto(
        n_g=6.0, municipio="Petrolina", uf="PE", pessoas_total=10.0,
        estrutura=Estrutura(comprimento_m=40, largura_m=20, altura_m=10),
        zonas=[ZonaEstudo(id_zona="Z", pessoas_na_zona=10.0,
                          sistemas_internos=[_sistema()])],
        linhas=[LinhaEletrica(id_linha="L1", trechos=[Trecho(comprimento_m=300)])],
    )
    for k, v in kw.items():
        setattr(p, k, v)
    p.zonas[0].sistemas_internos[0].sistema_independente = False
    p.zonas[0].sistemas_internos[0].ids_linhas = ["L1"]
    return p


def test_c1_l_a1():
    p = _projeto_minimo()
    z = p.zonas[0]
    z.r_t_chave = "marmore_ceramica"
    z.horas_presenca_ano = 4380
    esperado = 1e-3 * 1e-2 * (10 / 10) * 0.5 * 1.0
    assert perdas.l_a1(p, z) == pytest.approx(esperado)


def test_c3_l_b1_usa_l_f_da_tabela_c2():
    """Regressão do achado B-02."""
    p = _projeto_minimo()
    z = p.zonas[0]
    z.ocupacao = "industrial"
    z.r_p_chave, z.r_f_chave, z.h_z_chave = "automatica", "incendio_normal", "panico_alto"
    esperado = 0.2 * 1e-2 * 10.0 * 2e-2 * 1.0 * 1.0
    assert perdas.l_b1(p, z) == pytest.approx(esperado)


def test_c7_r_s_multiplica_as_perdas_de_l1():
    """Regressão do achado G-02."""
    p = _projeto_minimo()
    z = p.zonas[0]
    robusta = perdas.l_a1(p, z)
    z.r_s_chave = "simples"
    assert perdas.l_a1(p, z) == pytest.approx(2 * robusta)


def test_c3_4_risco_de_explosao_forca_r_p_igual_a_1():
    """C.3.4 — regressão do achado G-08."""
    z = ZonaEstudo(id_zona="Z", r_f_chave="explosao_zonas_1_21", r_p_chave="automatica")
    assert z.r_p == 1.0
    z.r_f_chave = "incendio_normal"
    assert z.r_p == pytest.approx(0.2)


def test_c3_2_perda_ambiental_soma_a_l_f():
    p = _projeto_minimo(perda_ambiental=True, l_fe=1.0, horas_presenca_externa_ano=4380)
    z = p.zonas[0]
    z.r_p_chave, z.r_f_chave = "nenhuma", "incendio_normal"
    l_ft = z.perdas["L_F_L1"] + 0.5
    assert perdas.l_b1(p, z) == pytest.approx(1.0 * 1e-2 * 1.0 * l_ft * 1.0 * 1.0)


def test_d1_nota_a_modo_representativo_substitui_razoes_por_um():
    p = _projeto_minimo(avaliar_r4=True, modo_r4="representativo")
    z = p.zonas[0]
    z.ocupacao = "comercial"
    z.valor_sistemas = 0.0     # razão seria 0 no modo detalhado
    assert perdas.l_c4(p, z) == pytest.approx(1e-2)


def test_d4_c_t_e_da_estrutura_e_nao_media_das_zonas():
    """Regressão do achado G-03."""
    p = _projeto_minimo(avaliar_r4=True, valor_total_estrutura=4_000_000)
    p.zonas = [
        ZonaEstudo(id_zona="Z1", pessoas_na_zona=5, valor_sistemas=1_000_000,
                   ocupacao="comercial", sistemas_internos=[_sistema()]),
        ZonaEstudo(id_zona="Z2", pessoas_na_zona=5, valor_sistemas=3_000_000,
                   ocupacao="comercial", sistemas_internos=[_sistema()]),
    ]
    soma = perdas.l_c4(p, p.zonas[0]) + perdas.l_c4(p, p.zonas[1])
    assert soma == pytest.approx(1e-2 * (4_000_000 / 4_000_000))


# =============================================================================
# Regras condicionais e composição de risco
# =============================================================================
def test_multizona_respeita_p_ta_de_cada_zona():
    """Regressão do achado B-03: o resultado não pode depender da ordem."""
    def monta(ordem):
        p = _projeto_minimo()
        za = ZonaEstudo(id_zona="A", pessoas_na_zona=5, p_ta_chaves=["nenhuma"],
                        r_t_chave="terra_concreto", r_f_chave="incendio_normal",
                        sistemas_internos=[_sistema(sistema_independente=False, ids_linhas=["L1"])])
        zb = ZonaEstudo(id_zona="B", pessoas_na_zona=5, p_ta_chaves=["restricoes_fisicas"],
                        r_t_chave="terra_concreto", r_f_chave="incendio_normal",
                        sistemas_internos=[_sistema(sistema_independente=False, ids_linhas=["L1"])])
        p.zonas = [za, zb] if ordem else [zb, za]
        return analise.analisar(p)

    assert monta(True).r1 == pytest.approx(monta(False).r1)


def test_zona_com_restricao_fisica_zera_r_a():
    p = _projeto_minimo()
    p.zonas[0].p_ta_chaves = ["restricoes_fisicas"]
    r = analise.analisar(p)
    assert r.componentes_r1()["R_A"] == 0.0


def test_tabela2_nota_a_derivada_do_risco_de_explosao():
    """Regressão do achado B-08: não pode depender de checkbox."""
    p = _projeto_minimo()
    p.zonas[0].ocupacao = "explosao"
    p.zonas[0].r_f_chave = "explosao_zonas_0_20"
    r = analise.analisar(p)
    assert r.inclui_falha_sistemas_em_r1
    assert r.componentes_r1()["R_C"] > 0
    assert r.componentes_r1()["R_M"] > 0


def test_tabela2_nota_a_derivada_de_hospital():
    p = _projeto_minimo()
    p.zonas[0].ocupacao = "hospital_uti"
    assert analise.analisar(p).inclui_falha_sistemas_em_r1


def test_componentes_de_falha_ausentes_em_ocupacao_comum():
    p = _projeto_minimo()
    p.zonas[0].ocupacao = "comercial"
    r = analise.analisar(p)
    assert not r.inclui_falha_sistemas_em_r1
    assert r.componentes_r1()["R_C"] == 0.0
    assert r.componentes_r1()["R_Z"] == 0.0


def test_r3_nao_aplicavel_sem_patrimonio_cultural():
    """Regressão do achado G-10: ausência não é aprovação."""
    r = analise.analisar(_projeto_minimo())
    assert r.r3_aplicavel is False
    assert r.r3_aprovado is None


def test_r3_aplicavel_com_patrimonio_cultural():
    p = _projeto_minimo(valor_total_estrutura=1_000_000)
    p.zonas[0].valor_patrimonio_cultural = 500_000
    p.zonas[0].ocupacao = "museu"
    r = analise.analisar(p)
    assert r.r3_aplicavel and r.r3 > 0


def test_f_t_criticidade_7_3_4():
    """Regressão do achado B-07."""
    assert _projeto_minimo(sistema_critico=True).f_t == 0.1
    assert _projeto_minimo(sistema_critico=False).f_t == 1.0


def test_f_inclui_as_seis_parcelas_da_tabela_7():
    """Regressão do achado G-07: F_B existe."""
    p = _projeto_minimo(p_b_chave="III")
    p.zonas[0].sistemas_internos[0].em_zpr0a = True
    r = analise.analisar(p)
    cf = r.componentes_f()
    assert set(cf) == {"F_B", "F_C", "F_M", "F_V", "F_W", "F_Z"}
    assert cf["F_B"] == pytest.approx(r.n_d * p.p_b)
    assert r.f == pytest.approx(sum(cf.values()))


def test_f_b_nulo_sem_equipamento_em_zpr0a():
    """7.1.5."""
    r = analise.analisar(_projeto_minimo(p_b_chave="III"))
    assert r.componentes_f()["F_B"] == 0.0


def test_f_v_usa_p_eb_conforme_tabela_7():
    p = _projeto_minimo(p_eb_chave="II")
    r = analise.analisar(p)
    ev = r.eventos_linhas["L1"]
    assert r.componentes_f()["F_V"] == pytest.approx(ev.n_l_mais_n_dj * 0.02)


def test_r1_e_soma_das_oito_componentes():
    p = _projeto_minimo()
    p.zonas[0].ocupacao = "explosao"
    p.zonas[0].r_f_chave = "explosao_zonas_0_20"
    r = analise.analisar(p)
    assert r.r1 == pytest.approx(sum(r.componentes_r1().values()))


def test_medidas_de_protecao_reduzem_o_risco():
    """Sanidade direcional: SPDA nível I e DPS têm de reduzir R1."""
    sem = analise.analisar(_projeto_minimo())
    com = analise.analisar(_projeto_minimo(p_b_chave="I", p_eb_chave="I"))
    assert com.r1 < sem.r1


def test_custo_anual_de_perda_usa_c_t_total():
    p = _projeto_minimo(avaliar_r4=True, valor_total_estrutura=2_000_000)
    p.zonas[0].valor_edificacao = 2_000_000
    r = analise.analisar(p)
    assert r.custo_anual_perda == pytest.approx(r.r4 * 2_000_000)


# =============================================================================
# Anexo F
# =============================================================================
def test_anexo_f_carrega_todos_os_municipios():
    todos = ng.carregar()
    assert len(todos) > 5500
    assert len(ng.ufs()) == 27


def test_anexo_f_petrolina():
    assert ng.buscar("Petrolina", "PE").ng == 6.0


def test_anexo_f_busca_ignora_acento_e_caixa():
    assert ng.procurar("sao paulo")


# =============================================================================
# Validação
# =============================================================================
def test_validacao_aceita_projeto_consistente():
    assert not tem_erro(validar(_projeto_minimo()))


def test_validacao_rejeita_soma_de_pessoas_maior_que_total():
    p = _projeto_minimo(pessoas_total=5.0)
    p.zonas[0].pessoas_na_zona = 50.0
    assert tem_erro(validar(p))


def test_validacao_rejeita_n_g_sobrescrito_sem_justificativa():
    p = _projeto_minimo(n_g_sobrescrito=True, n_g_justificativa="")
    assert tem_erro(validar(p))


def test_validacao_exige_sistema_interno_na_zona():
    p = _projeto_minimo()
    p.zonas[0].sistemas_internos = []
    assert tem_erro(validar(p))


def test_validacao_exige_c_t_para_r4_detalhado():
    p = _projeto_minimo(avaliar_r4=True, modo_r4="detalhado", valor_total_estrutura=0)
    assert tem_erro(validar(p))


def test_validacao_rejeita_blindagem_no_bep_sem_blindagem():
    p = _projeto_minimo()
    p.linhas[0].blindagem_no_mesmo_bep = True
    assert tem_erro(validar(p))


def test_validacao_rejeita_neutro_multiaterrado_em_linha_de_sinal():
    p = _projeto_minimo()
    p.linhas[0].tipo = "sinal"
    p.linhas[0].neutro_multiaterrado = True
    assert tem_erro(validar(p))


# =============================================================================
# Serialização
# =============================================================================
def test_projeto_sobrevive_a_ida_e_volta_em_json():
    p = _projeto_minimo(avaliar_r4=True, valor_total_estrutura=1_000_000)
    volta = de_json(para_json(p))
    assert analise.analisar(volta).r1 == pytest.approx(analise.analisar(p).r1)
    assert impressao_digital(volta) == impressao_digital(p)


def test_hash_muda_com_qualquer_alteracao_de_entrada():
    p = _projeto_minimo()
    antes = impressao_digital(p)
    p.estrutura.altura_m += 0.01
    assert impressao_digital(p) != antes


def test_clonagem_permite_comparar_cenarios():
    base = _projeto_minimo()
    protegido = clonar(base)
    protegido.p_b_chave = "I"
    assert base.p_b_chave == "nenhum"
    assert analise.analisar(protegido).r1 < analise.analisar(base).r1
