"""Modelo de dados do projeto de análise de risco.

Hierarquia, espelhando a norma:

    Projeto
    ├── Estrutura                    (A.2 — geometria, C_D)
    ├── Zona de estudo  [1..n]       (6.7 — características homogêneas)
    │   └── Sistema interno [1..n]   (6.9.1.2 b — composição de P_C e P_M)
    └── Linha elétrica  [1..n]       (6.8 — dividida em trechos S_L)
        ├── Trecho [1..n]
        └── Estrutura adjacente (opcional, Figura A.5)

Decisão de projeto que corrige o achado B-03: TODA medida de proteção de
característica zonal (P_TA, P_TU, K_S1, K_S2) mora na Zona, e toda característica
de equipamento (U_W, K_S3, P_SPD) mora no Sistema Interno. Nenhum parâmetro de
zona é lido de `zonas[0]`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, fields

from . import tabelas as T


class CoerceFloat:
    """Garante que todo campo anotado como float seja mesmo float.

    Motivo prático: `Estrutura(comprimento_m=40)` deixaria um int no campo, e
    tanto os widgets numéricos da interface quanto a serialização passam a se
    comportar de forma inconsistente. Coerção na fronteira do modelo resolve
    para todos os consumidores de uma vez.
    """

    def __post_init__(self) -> None:
        for f in fields(self):
            if f.type in ("float", float):
                v = getattr(self, f.name)
                if v is not None and not isinstance(v, float):
                    setattr(self, f.name, float(v))
            elif f.type in ("float | None", "Optional[float]"):
                v = getattr(self, f.name)
                if v is not None and not isinstance(v, float):
                    setattr(self, f.name, float(v))


# =============================================================================
# Estrutura
# =============================================================================
@dataclass
class Estrutura(CoerceFloat):
    """A.2 — estrutura a ser protegida."""

    comprimento_m: float = 0.0          # L
    largura_m: float = 0.0              # W
    altura_m: float = 0.0               # H (altura mínima do corpo principal)
    altura_saliencia_m: float = 0.0     # H_P (saliência elevada na cobertura)
    c_d_chave: str = "isolada"          # Tabela A.1

    # A.2.1.3.1: forma complexa exige método gráfico. Quando o projetista
    # determinar A_D graficamente, informa o valor e o motor o usa tal qual.
    a_d_informada_m2: float | None = None
    a_d_justificativa: str = ""

    @property
    def c_d(self) -> float:
        return T.valor(T.C_D, self.c_d_chave)

    def a_d(self) -> float:
        """Área de exposição equivalente A_D — eq. (A.1) e (A.2)."""
        if self.a_d_informada_m2 is not None:
            return float(self.a_d_informada_m2)
        L, W, H = self.comprimento_m, self.largura_m, self.altura_m
        a_principal = L * W + 2 * (3 * H) * (L + W) + math.pi * (3 * H) ** 2
        # A.2.1.3.2: valor aceitável é o MAIOR entre A_D(H_mín) e π(3·H_P)².
        a_saliencia = math.pi * (3 * self.altura_saliencia_m) ** 2
        return max(a_principal, a_saliencia)

    def a_m(self) -> float:
        """Área de exposição de descargas próximas — eq. (A.6)."""
        return 2 * 500 * (self.comprimento_m + self.largura_m) + math.pi * 500**2


@dataclass
class EstruturaAdjacente(CoerceFloat):
    """Estrutura conectada à extremidade de uma linha elétrica (Figura A.5)."""

    comprimento_m: float = 0.0
    largura_m: float = 0.0
    altura_m: float = 0.0
    c_dj_chave: str = "isolada"

    @property
    def c_dj(self) -> float:
        return T.valor(T.C_D, self.c_dj_chave)

    def a_dj(self) -> float:
        L, W, H = self.comprimento_m, self.largura_m, self.altura_m
        return L * W + 2 * (3 * H) * (L + W) + math.pi * (3 * H) ** 2


# =============================================================================
# Linha elétrica e trechos
# =============================================================================
@dataclass
class Trecho(CoerceFloat):
    """6.8 — trecho S_L de uma linha elétrica."""

    id_trecho: str = "Trecho 1"
    comprimento_m: float = 1000.0       # L_L (A.4.1: 1 000 m se desconhecido)
    c_i_chave: str = "aereo"            # Tabela A.2
    c_e_chave: str = "rural"            # Tabela A.4
    c_t_chave: str = "bt_ou_sinal"      # Tabela A.3
    resistividade_solo_ohm_m: float = 400.0   # ρ, só relevante se enterrado

    @property
    def c_i(self) -> float:
        return T.valor(T.C_I, self.c_i_chave)

    @property
    def c_e(self) -> float:
        return T.valor(T.C_E, self.c_e_chave)

    @property
    def c_t(self) -> float:
        return T.valor(T.C_T, self.c_t_chave)

    @property
    def enterrado(self) -> bool:
        return self.c_i_chave in ("enterrado", "enterrado_em_malha")

    def a_l(self) -> float:
        """Eq. (A.8) e nota 1 da Tabela A.2."""
        if self.enterrado and self.resistividade_solo_ohm_m > 400.0:
            return 0.6 * math.sqrt(self.resistividade_solo_ohm_m) * self.comprimento_m
        return 40.0 * self.comprimento_m

    def a_i(self) -> float:
        """Eq. (A.10)."""
        return 4000.0 * self.comprimento_m


@dataclass
class LinhaEletrica(CoerceFloat):
    """Linha elétrica conectada à estrutura, com seus trechos e blindagem."""

    id_linha: str = "Linha 1"
    tipo: str = "energia"                       # 'energia' | 'sinal'
    trechos: list[Trecho] = field(default_factory=lambda: [Trecho()])
    estrutura_adjacente: EstruturaAdjacente | None = None

    # --- Atributos declarados que alimentam a Tabela B.4 e a Tabela B.8 ------
    blindada: bool = False
    resistencia_blindagem_ohm_km: float = 20.0
    blindagem_no_mesmo_bep: bool = False
    cabo_protecao_ou_conduto_metalico: bool = False
    interface_isolante: bool = False
    interface_isolante_protegida_por_dps: bool = False
    neutro_multiaterrado: bool = False          # só declarável para energia
    sem_linha_externa: bool = False             # sistema independente / fibra

    @property
    def instalacao_subterranea(self) -> bool:
        """B.4: a distinção aérea/subterrânea vale para a linha como um todo.
        Adota-se subterrânea somente se TODOS os trechos forem enterrados —
        um único trecho aéreo mantém o valor de C_LI mais desfavorável (0,1)."""
        return bool(self.trechos) and all(t.enterrado for t in self.trechos)

    @property
    def c_t_mais_desfavoravel(self) -> float:
        """6.8.2 — havendo mais de um valor no trecho, adota-se o que leva ao
        maior risco. Usado em N_DJ, que é da linha e não do trecho."""
        return max((t.c_t for t in self.trechos), default=1.0)

    def c_ld_c_li(self) -> tuple[float, float]:
        """Tabela B.4 aplicada aos atributos declarados desta linha."""
        return T.valor_c_ld_c_li(
            sem_linha_externa=self.sem_linha_externa,
            interface_isolante=self.interface_isolante,
            interface_isolante_protegida_por_dps=self.interface_isolante_protegida_por_dps,
            cabo_protecao_ou_conduto_metalico=self.cabo_protecao_ou_conduto_metalico,
            blindada=self.blindada,
            blindagem_no_mesmo_bep=self.blindagem_no_mesmo_bep,
            instalacao_subterranea=self.instalacao_subterranea,
            neutro_multiaterrado=self.neutro_multiaterrado and self.tipo == "energia",
        )

    @property
    def faixa_p_ld(self) -> str:
        """Linha da Tabela B.8 aplicável. A blindagem só é creditada quando
        interligada à mesma referência de equipotencialização do equipamento."""
        if not (self.blindada and self.blindagem_no_mesmo_bep):
            return "nao_creditada"
        return T.faixa_rs(self.resistencia_blindagem_ohm_km)


# =============================================================================
# Sistema interno
# =============================================================================
@dataclass
class SistemaInterno(CoerceFloat):
    """Sistema eletroeletrônico interno de uma zona.

    É a unidade sobre a qual as equações (12) e (13) compõem P_C e P_M — e não
    a linha elétrica, como fazia a versão anterior (achado G-05).
    """

    id_sistema: str = "Sistema 1"
    uw_kv: float = 2.5                  # U_W do equipamento mais vulnerável
    blindado: bool = False              # B.4.4: se não blindado, C_LD = 1 em P_C
    p_spd_chave: str = "nenhum"         # Tabela B.3
    k_s3_chave: str = "nao_blindado_sem_roteamento"   # Tabela B.5
    interface_optica: bool = False      # B.4.11 → P_MS = 0
    atende_normas_de_produto: bool = True  # B.4.10: se não atende, P_M = 1
    ids_linhas: list[str] = field(default_factory=list)  # linhas a que se conecta
    sistema_independente: bool = False  # B.4 / Tabela B.4: sem linhas externas
    em_zpr0a: bool = False              # 7.1.5 — habilita F_B

    @property
    def p_spd(self) -> float:
        return T.valor(T.P_SPD, self.p_spd_chave)

    @property
    def k_s3(self) -> float:
        return T.valor(T.K_S3, self.k_s3_chave)

    @property
    def k_s4(self) -> float:
        """B.4.14 — K_S4 = 1/U_W, limitado a 1."""
        return min(1.0 / max(self.uw_kv, 1e-6), 1.0)


# =============================================================================
# Zona de estudo
# =============================================================================
@dataclass
class ZonaEstudo(CoerceFloat):
    """6.7 — zona de estudo Z_S com características homogêneas."""

    id_zona: str = "Zona 1"
    ocupacao: str = "outros"                       # define L_F e L_O (C.2/C.9/D.2)

    # --- pessoas (C.3.1) ---
    pessoas_na_zona: float = 1.0                   # n_z
    horas_presenca_ano: float = 8760.0             # t_z

    # --- fatores de perda ---
    r_t_chave: str = "terra_concreto"              # Tabela C.3
    r_p_chave: str = "nenhuma"                     # Tabela C.4
    r_f_chave: str = "incendio_baixo"              # Tabela C.5
    h_z_chave: str = "sem_perigo"                  # Tabela C.6
    r_s_chave: str = "robusta"                     # Tabela C.7

    # --- medidas de proteção da zona ---
    p_ta_chaves: list[str] = field(default_factory=lambda: ["nenhuma"])  # B.1 (produto)
    p_tu_chaves: list[str] = field(default_factory=lambda: ["nenhuma"])  # B.6 (produto)

    # --- blindagem espacial (B.4.12) ---
    blindagem_continua_zpr01: bool = False   # ⇒ K_S1 = 1e-4
    blindagem_continua_zprxy: bool = False   # ⇒ K_S2 = 1e-4
    largura_malha_zpr01_m: float = 0.0       # w_m1
    largura_malha_zprxy_m: float = 0.0       # w_m2
    rede_equipotencial_em_malha: bool = False  # nota de B.4.12 ⇒ K_S1, K_S2 /2

    # --- valores econômicos na zona (Anexo D) ---
    valor_animais: float = 0.0        # c_a
    valor_edificacao: float = 0.0     # c_b
    valor_conteudo: float = 0.0       # c_c
    valor_sistemas: float = 0.0       # c_s
    valor_patrimonio_cultural: float = 0.0  # c_z

    sistemas_internos: list[SistemaInterno] = field(default_factory=list)

    # ---------------------------------------------------------------- fatores
    @property
    def risco_de_explosao(self) -> bool:
        return self.r_f_chave in T.RF_COM_RISCO_EXPLOSAO

    @property
    def r_t(self) -> float:
        return T.valor(T.R_T, self.r_t_chave)

    @property
    def r_p(self) -> float:
        """C.3.4 — em estrutura com risco de explosão, r_p = 1 sempre."""
        if self.risco_de_explosao:
            return 1.0
        return T.valor(T.R_P, self.r_p_chave)

    @property
    def r_f(self) -> float:
        return T.valor(T.R_F, self.r_f_chave)

    @property
    def h_z(self) -> float:
        return T.valor(T.H_Z, self.h_z_chave)

    @property
    def r_s(self) -> float:
        """Fator de construção da Tabela C.7 (não confundir com R_S, a
        resistência da blindagem do cabo, da Tabela B.8)."""
        return T.valor(T.R_S_CONSTRUCAO, self.r_s_chave)

    @property
    def p_ta(self) -> float:
        """Tabela B.1 com a regra B.2.2 (produto das medidas adotadas)."""
        v = 1.0
        for c in self.p_ta_chaves or ["nenhuma"]:
            v *= T.valor(T.P_TA, c)
        return v

    @property
    def p_tu(self) -> float:
        """Tabela B.6 com a nota 1 (produto das medidas adotadas)."""
        v = 1.0
        for c in self.p_tu_chaves or ["nenhuma"]:
            v *= T.valor(T.P_TU, c)
        return v

    def k_s1(self) -> float:
        """B.4.12 — eq. (B.5), limitado a 1."""
        if self.blindagem_continua_zpr01:
            return 1e-4
        if self.largura_malha_zpr01_m <= 0:
            return 1.0
        k = min(0.12 * self.largura_malha_zpr01_m, 1.0)
        return k / 2.0 if self.rede_equipotencial_em_malha else k

    def k_s2(self) -> float:
        """B.4.12 — eq. (B.6), limitado a 1."""
        if self.blindagem_continua_zprxy:
            return 1e-4
        if self.largura_malha_zprxy_m <= 0:
            return 1.0
        k = min(0.12 * self.largura_malha_zprxy_m, 1.0)
        return k / 2.0 if self.rede_equipotencial_em_malha else k

    @property
    def perdas(self) -> dict:
        return T.perdas_da_ocupacao(self.ocupacao)


# =============================================================================
# Projeto
# =============================================================================
@dataclass
class Identificacao:
    """Dados que tornam o laudo um documento técnico, e não uma planilha."""

    obra: str = ""
    endereco: str = ""
    proprietario: str = ""
    responsavel_tecnico: str = ""
    crea: str = ""
    art: str = ""
    data_emissao: str = ""


@dataclass
class Projeto(CoerceFloat):
    identificacao: Identificacao = field(default_factory=Identificacao)

    municipio: str = ""
    uf: str = ""
    n_g: float = 0.0
    n_g_sobrescrito: bool = False
    n_g_justificativa: str = ""

    estrutura: Estrutura = field(default_factory=Estrutura)
    zonas: list[ZonaEstudo] = field(default_factory=list)
    linhas: list[LinhaEletrica] = field(default_factory=list)

    # --- medidas de proteção de âmbito estrutural ---
    p_b_chave: str = "nenhum"                  # Tabela B.2 (SPDA externo)
    p_eb_chave: str = "sem_dps_classe_I"       # Tabela B.7 (DPS classe I na entrada)

    # --- pessoas ---
    pessoas_total: float = 1.0                 # n_t

    # --- frequência de danos ---
    sistema_critico: bool = False              # 7.3.3 ⇒ F_T = 0,1 (7.3.4)

    # --- Anexo D ---
    avaliar_r4: bool = False
    modo_r4: str = "detalhado"                 # 'detalhado' | 'representativo'
    valor_total_estrutura: float = 0.0         # c_t — DA ESTRUTURA, não da zona

    # --- perda ambiental (C.3.2 / D.3.2) ---
    perda_ambiental: bool = False
    l_fe: float = 1.0                          # nota 1 de C.3.2
    horas_presenca_externa_ano: float = 8760.0  # t_e
    valores_externos: float = 0.0              # c_e (D.3.2)

    observacoes: str = ""

    @property
    def p_b(self) -> float:
        return T.valor(T.P_B, self.p_b_chave)

    @property
    def p_eb(self) -> float:
        return T.valor(T.P_EB, self.p_eb_chave)

    @property
    def tem_risco_de_explosao(self) -> bool:
        return any(z.risco_de_explosao for z in self.zonas)

    @property
    def falha_de_sistema_ameaca_vida(self) -> bool:
        """Nota `a` da Tabela 2 — condição para R_C, R_M, R_W e R_Z comporem R1.

        É DERIVADA, nunca um checkbox solto: basta que a zona tenha risco de
        explosão, ou que a ocupação atribua L_O > 0 pela Tabela C.2 (hospital),
        para que a norma torne essas componentes obrigatórias.
        """
        if self.tem_risco_de_explosao:
            return True
        return any(z.perdas["L_O_L1"] > 0.0 for z in self.zonas)

    @property
    def f_t(self) -> float:
        return T.F_T_CRITICO if self.sistema_critico else T.F_T_NAO_CRITICO

    def l_e_para_l1(self) -> float:
        """C.3.2 — eq. (C.6)."""
        if not self.perda_ambiental:
            return 0.0
        return self.l_fe * min(self.horas_presenca_externa_ano, 8760.0) / 8760.0

    def l_e_para_l4(self) -> float:
        """D.3.2 — eq. (D.6)."""
        if not self.perda_ambiental or self.valor_total_estrutura <= 0:
            return 0.0
        return self.l_fe * self.valores_externos / self.valor_total_estrutura
