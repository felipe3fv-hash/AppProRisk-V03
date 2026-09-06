"""Tabelas normativas da ABNT NBR 5419-2:2026, transcritas como dados.

Princípio: nenhuma tabela da norma é reescrita como cadeia de `if`. Toda tabela
é um literal indexado, e a suíte de testes percorre célula a célula. Foi
exatamente a ausência disso que produziu os oito desvios de P_LD da versão
anterior.

Cada estrutura abaixo cita a tabela de origem. Rótulos são o texto da norma,
para que a interface e o laudo mostrem ao usuário a mesma linguagem da norma.
"""

from __future__ import annotations

from bisect import bisect_right

# =============================================================================
# ANEXO A — número anual de eventos perigosos
# =============================================================================

# Tabela A.1 — Fator de localização da estrutura C_D (também C_DJ)
C_D = {
    "cercada_objetos_mais_altos": (0.25, "Estrutura cercada por objetos significativamente mais altos"),
    "cercada_mesma_altura": (0.5, "Estrutura cercada por objetos da mesma altura ou ligeiramente mais baixos"),
    "isolada": (1.0, "Estrutura isolada: nenhum outro objeto nas vizinhanças ou cercada por objetos significativamente mais baixos"),
    "topo_de_colina": (2.0, "Estrutura isolada no topo de uma colina ou monte"),
}

# Tabela A.2 — Fator de instalação da linha elétrica C_I
C_I = {
    "aereo": (1.0, "Aéreo"),
    "enterrado": (0.5, "Enterrado"),
    "enterrado_em_malha": (0.01, "Enterrado no interior dos limites de um eletrodo de aterramento em malha (NBR 5419-4:2026, 5.2)"),
}

# Tabela A.3 — Fator do tipo de linha elétrica C_T
C_T = {
    "bt_ou_sinal": (1.0, "Linha elétrica de energia em BT ou de sinal"),
    "at_com_trafo": (0.2, "Linha elétrica de energia em AT (com transformador AT/BT com enrolamentos eletricamente separados)"),
}

# Tabela A.4 — Fator ambiental da linha elétrica C_E
C_E = {
    "rural": (1.0, "Rural"),
    "suburbano": (0.5, "Suburbano"),
    "urbano": (0.1, "Urbano"),
    "urbano_acima_20m": (0.01, "Urbano com estruturas acima de 20 m de altura"),
}

# =============================================================================
# ANEXO B — probabilidades de dano
# =============================================================================

# Tabela B.1 — P_TA (choque por tensões de toque e passo, descarga na estrutura)
# B.2.2: se mais de uma medida for tomada, P_TA é o PRODUTO dos valores.
P_TA = {
    "nenhuma": (1.0, "Nenhuma medida de proteção"),
    "avisos_alerta": (1e-1, "Avisos de alerta (usar após análise de viabilidade)"),
    "isolacao_eletrica": (1e-2, "Isolação elétrica (mín. 3 mm de polietileno reticulado nas descidas) — só tensão de toque"),
    "malha_equipotencial_solo": (1e-2, "Malha de equipotencialização do solo por eletrodo reticulado — só tensão de passo"),
    "estrutura_metalica_continua": (1e-3, "Estrutura metálica contínua ou concreto armado como subsistema de descida natural"),
    "restricoes_fisicas": (0.0, "Restrições físicas fixas (toque e passo)"),
}

# Tabela B.2 — P_B (danos físicos, em função do NP do SPDA)
P_B = {
    "nenhum": (1.0, "Estrutura não protegida por SPDA"),
    "IV": (0.2, "SPDA nível IV"),
    "III": (0.1, "SPDA nível III"),
    "II": (0.05, "SPDA nível II"),
    "I": (0.02, "SPDA nível I"),
    "captacao_NPI_descida_natural": (0.01, "Captação conforme NP I + estrutura metálica contínua ou concreto armado como descida natural (NBR 5419-3:2026, 8.1.2-b)"),
    "cobertura_metalica_descida_natural": (0.001, "Cobertura metálica como captação natural, instalações da cobertura protegidas + descida natural (NBR 5419-3:2026, 8.1.2-b)"),
}

# Tabela B.3 — P_SPD (sistema coordenado de DPS)
P_SPD = {
    "nenhum": (1.0, "Nenhum sistema coordenado de DPS"),
    "III-IV": (0.05, "DPS coordenado NP III-IV"),
    "II": (0.02, "DPS coordenado NP II"),
    "I": (0.01, "DPS coordenado NP I"),
    "melhor_que_I": (0.005, "Melhor do que NP I (faixa 0,005 a 0,001 — adotado o extremo conservador)"),
}

# Tabela B.7 — P_EB (ligação equipotencial por DPS classe I na entrada)
P_EB = {
    "sem_dps_classe_I": (1.0, "Sem DPS classe I"),
    "III-IV": (0.05, "DPS classe I NP III-IV"),
    "II": (0.02, "DPS classe I NP II"),
    "I": (0.01, "DPS classe I NP I"),
    "melhor_que_I": (0.005, "Melhor do que NP I (faixa 0,005 a 0,001 — adotado o extremo conservador)"),
}

# Tabela B.6 — P_TU (choque por tensão de toque, descarga na linha)
# Nota 1: se mais de uma medida for tomada, P_TU é o PRODUTO dos valores.
P_TU = {
    "nenhuma": (1.0, "Nenhuma medida de proteção"),
    "avisos_alerta": (1e-1, "Avisos visíveis de alerta"),
    "isolacao_eletrica": (1e-2, "Isolação elétrica"),
    "restricoes_fisicas": (0.0, "Restrições físicas"),
}

# Tabela B.5 — K_S3 (características da fiação interna)
K_S3 = {
    "nao_blindado_sem_roteamento": (1.0, "Cabo não blindado, sem preocupação de roteamento (laços ~50 m²)"),
    "nao_blindado_evita_grandes_lacos": (0.5, "Cabo não blindado, roteamento evita grandes laços (~25 m²)"),
    "nao_blindado_evita_lacos_medios": (0.2, "Cabo não blindado, roteamento evita laços médios (~10 m²)"),
    "nao_blindado_evita_pequenos_lacos": (0.01, "Cabo não blindado, roteamento evita pequenos laços (~0,5 m²)"),
    "blindado_ou_conduto_metalico": (0.0001, "Cabos blindados ou instalados em condutos metálicos, interligados nas duas extremidades"),
}

# --- Tabela B.8 — P_LD -------------------------------------------------------
# Colunas: tensão suportável nominal de impulso U_W do EQUIPAMENTO, em kV.
UW_COLUNAS_PLD = (0.35, 0.5, 1.0, 1.5, 2.5, 4.0, 6.0)

P_LD_LINHAS = {
    # Linha aérea ou subterrânea, não blindada, OU blindagem não interligada
    # à mesma referência de equipotencialização do equipamento.
    "nao_creditada": (1.0, 1.0, 1.0, 1.0, 1.00, 1.00, 1.00),
    # Blindada, aérea ou subterrânea, blindagem interligada ao mesmo BEP:
    "rs_5_a_20": (1.0, 1.0, 1.0, 1.0, 0.95, 0.90, 0.80),   # 5 < R_S <= 20 Ω/km
    "rs_1_a_5": (1.0, 1.0, 0.9, 0.8, 0.60, 0.30, 0.10),    # 1 < R_S <= 5 Ω/km
    "rs_ate_1": (1.0, 0.85, 0.6, 0.4, 0.20, 0.04, 0.02),   # R_S <= 1 Ω/km
}

# --- Tabela B.9 — P_LI -------------------------------------------------------
UW_COLUNAS_PLI = (1.0, 1.5, 2.5, 4.0, 6.0)
P_LI_LINHAS = {
    "energia": (1.0, 0.6, 0.3, 0.16, 0.10),
    "sinal": (1.0, 0.5, 0.2, 0.08, 0.04),
}


def _coluna_uw(uw_kv: float, colunas: tuple) -> int:
    """Índice da coluna de U_W a aplicar.

    A norma tabela valores discretos de U_W. Para um U_W intermediário adota-se
    a maior coluna tabelada MENOR OU IGUAL ao valor informado — o que é sempre
    conservador, já que P_LD e P_LI decrescem com U_W. Abaixo da primeira
    coluna, usa-se a primeira (pior caso).
    """
    if uw_kv < colunas[0]:
        return 0
    return bisect_right(colunas, uw_kv + 1e-12) - 1


def faixa_rs(r_s_ohm_km: float) -> str:
    """Faixa de resistência de blindagem da Tabela B.8."""
    if r_s_ohm_km <= 1.0:
        return "rs_ate_1"
    if r_s_ohm_km <= 5.0:
        return "rs_1_a_5"
    if r_s_ohm_km <= 20.0:
        return "rs_5_a_20"
    # Acima de 20 Ω/km a norma não credita a blindagem.
    return "nao_creditada"


def valor_p_ld(linha_tabela: str, uw_kv: float) -> float:
    """Tabela B.8, célula (faixa de R_S, U_W)."""
    return P_LD_LINHAS[linha_tabela][_coluna_uw(uw_kv, UW_COLUNAS_PLD)]


def valor_p_li(tipo_linha: str, uw_kv: float) -> float:
    """Tabela B.9, célula (tipo de linha, U_W)."""
    return P_LI_LINHAS[tipo_linha][_coluna_uw(uw_kv, UW_COLUNAS_PLI)]


# --- Tabela B.4 — C_LD e C_LI ------------------------------------------------
# Modelada como decisão sobre atributos DECLARADOS da linha, na ordem de
# especificidade da tabela. Nada é inferido: uma característica não declarada
# cai na linha "nenhuma ou indefinida", que é (1, 1).

def valor_c_ld_c_li(
    *,
    sem_linha_externa: bool = False,
    interface_isolante: bool = False,
    interface_isolante_protegida_por_dps: bool = False,
    cabo_protecao_ou_conduto_metalico: bool = False,
    blindada: bool = False,
    blindagem_no_mesmo_bep: bool = False,
    instalacao_subterranea: bool = False,
    neutro_multiaterrado: bool = False,
) -> tuple[float, float]:
    """Tabela B.4 — retorna (C_LD, C_LI).

    Nota `a` da Tabela B.4: com interface isolante, C_LD = 0 SOMENTE se a
    interface for protegida por DPS (ou ensaiada com U_W superior ao previsto
    no ponto). Nos demais casos C_LD = 1.
    """
    if sem_linha_externa:
        return (0.0, 0.0)
    if interface_isolante:
        return (0.0 if interface_isolante_protegida_por_dps else 1.0, 0.0)
    if cabo_protecao_ou_conduto_metalico and blindagem_no_mesmo_bep:
        return (0.0, 0.0)
    if blindada and blindagem_no_mesmo_bep:
        return (1.0, 0.0)
    if blindada:
        return (1.0, 0.3 if instalacao_subterranea else 0.1)
    if neutro_multiaterrado:
        return (1.0, 0.2)
    return (1.0, 1.0)


# =============================================================================
# ANEXO C — quantidade de perda (L1 e L3)
# =============================================================================

# Tabela C.3 — fator de redução r_t (tipo de superfície do solo ou piso)
R_T = {
    "terra_concreto": (1e-2, "Terra, concreto (≤ 1 kΩ)"),
    "marmore_ceramica": (1e-3, "Mármore, cerâmica (1 a 10 kΩ)"),
    "brita_tapete_carpete": (1e-4, "Brita, tapete, carpete (10 a 100 kΩ)"),
    "asfalto_linoleo_madeira": (1e-5, "Asfalto, linóleo, madeira (≥ 100 kΩ)"),
}

# Tabela C.4 — fator de redução r_p (providências contra incêndio)
# C.3.3: havendo mais de uma providência, adota-se o MENOR valor aplicável.
# C.3.4: em estruturas com risco de explosão, r_p = 1 em todos os casos.
R_P = {
    "nenhuma": (1.0, "Nenhuma providência, ou parte da estrutura com risco de explosão"),
    "manual": (0.5, "Extintores, instalações fixas manuais, alarme manual, hidrantes, compartimentos à prova de fogo ou rotas de escape"),
    "automatica": (0.2, "Instalações fixas automáticas ou alarme automático (protegidos contra sobretensões)"),
}

# Tabela C.5 — fator de redução r_f (risco de incêndio ou explosão)
R_F = {
    "explosao_zonas_0_20": (1.0, "Explosão — zonas 0, 20 e explosivos sólidos"),
    "explosao_zonas_1_21": (1e-1, "Explosão — zonas 1, 21"),
    "explosao_zonas_2_22": (1e-3, "Explosão — zonas 2, 22"),
    "incendio_alto": (1e-1, "Incêndio — risco alto (carga de incêndio ≥ 800 MJ/m²)"),
    "incendio_normal": (1e-2, "Incêndio — risco normal (400 a 800 MJ/m²)"),
    "incendio_baixo": (1e-3, "Incêndio — risco baixo (< 400 MJ/m²)"),
    "nenhum": (0.0, "Nenhum risco de incêndio ou explosão"),
}

# Chaves de r_f que caracterizam ESTRUTURA COM RISCO DE EXPLOSÃO. Disparam
# duas regras normativas obrigatórias:
#   - C.3.4      : r_p = 1 obrigatoriamente;
#   - Tabela 2,a : R_C, R_M, R_W e R_Z passam a compor R1.
RF_COM_RISCO_EXPLOSAO = frozenset(
    {"explosao_zonas_0_20", "explosao_zonas_1_21", "explosao_zonas_2_22"}
)

# Tabela C.6 — fator h_z (perigo especial)
H_Z = {
    "sem_perigo": (1.0, "Sem perigo especial"),
    "panico_baixo": (2.0, "Baixo nível de pânico (até dois andares e no máximo 100 pessoas)"),
    "panico_medio": (5.0, "Nível médio de pânico (eventos culturais/esportivos, 100 a 1 000 pessoas)"),
    "dificuldade_evacuacao": (5.0, "Dificuldade de evacuação (pessoas imobilizadas, hospitais)"),
    "panico_alto": (10.0, "Alto nível de pânico (eventos culturais/esportivos com mais de 1 000 pessoas)"),
}

# Tabela C.7 — fator r_s (tipo de construção)
R_S_CONSTRUCAO = {
    "robusta": (1.0, "Robusta: estrutura metálica ou concreto armado"),
    "simples": (2.0, "Simples: madeira ou alvenaria simples"),
}

# L_T é único para todos os tipos de estrutura (Tabelas C.2 e D.2).
L_T_L1 = 1e-2
L_T_L4 = 1e-2

# Tabela C.9 — L_F para perda de patrimônio cultural (L3)
L_F_L3 = 1e-1


# --- Ocupação: uma escolha que preenche as TRÊS tabelas de perda -------------
# Colunas: (L_F por C.2, L_O por C.2, L_F por D.2, L_O por D.2)
#
# Observação normativa importante: a Tabela C.2 só define L_O (perda de vida por
# falha de sistemas internos) para risco de explosão, UTI/bloco cirúrgico e
# demais partes de hospital. Para as demais ocupações L_O = 0 em L1 — o que é
# coerente com a nota `a` da Tabela 2, que restringe R_C1/R_M1/R_W1/R_Z1
# exatamente a esses casos.
OCUPACOES = {
    "explosao":            ("Estrutura com risco de explosão",            1e-1, 1e-1, 1.0,  1e-1),
    "hospital_uti":        ("Hospital — UTI e bloco cirúrgico",           1e-1, 1e-2, 0.5,  1e-2),
    "hospital_outras":     ("Hospital — demais partes",                   1e-1, 1e-3, 0.5,  1e-2),
    "hotel":               ("Hotel",                                      1e-1, 0.0,  0.2,  1e-2),
    "escola":              ("Escola",                                     1e-1, 0.0,  0.2,  1e-3),
    "edificio_civico":     ("Edifício cívico",                            1e-1, 0.0,  0.1,  1e-4),
    "entretenimento":      ("Entretenimento público",                     5e-2, 0.0,  0.2,  1e-3),
    "igreja":              ("Igreja",                                     5e-2, 0.0,  0.2,  1e-3),
    "museu":               ("Museu, galeria",                             5e-2, 0.0,  0.5,  1e-3),
    "industrial":          ("Industrial",                                 2e-2, 0.0,  0.5,  1e-2),
    "comercial":           ("Comercial",                                  2e-2, 0.0,  0.2,  1e-2),
    "escritorio":          ("Escritório",                                 1e-2, 0.0,  0.2,  1e-2),
    "agricultura":         ("Agricultura",                                1e-2, 0.0,  0.5,  1e-3),
    "outros":              ("Outros",                                     1e-2, 0.0,  0.1,  1e-4),
}


def perdas_da_ocupacao(chave: str) -> dict:
    """Devolve L_F e L_O separados por tipo de perda, a partir da ocupação."""
    rotulo, lf1, lo1, lf4, lo4 = OCUPACOES[chave]
    return {
        "rotulo": rotulo,
        "L_F_L1": lf1,   # Tabela C.2
        "L_O_L1": lo1,   # Tabela C.2
        "L_F_L3": L_F_L3,  # Tabela C.9
        "L_F_L4": lf4,   # Tabela D.2
        "L_O_L4": lo4,   # Tabela D.2
        "L_T_L1": L_T_L1,
        "L_T_L4": L_T_L4,
    }


# =============================================================================
# Limites — Tabela 4 (R_T), 7.3.4 (F_T), D.1.2 (R_T de R4)
# =============================================================================
R_T_R1 = 1e-5   # Tabela 4 — perda de vida humana ou ferimentos permanentes
R_T_R3 = 1e-4   # Tabela 4 — perda de patrimônio cultural
R_T_R4 = 1e-3   # D.1.2 — valor representativo, informativo
F_T_CRITICO = 0.1      # 7.3.4 — não pode ser alterado
F_T_NAO_CRITICO = 1.0  # 7.3.4 — meramente representativo


def rotulo(tabela: dict, chave: str) -> str:
    return tabela[chave][1]


def valor(tabela: dict, chave: str) -> float:
    return tabela[chave][0]
