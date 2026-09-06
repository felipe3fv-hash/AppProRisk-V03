"""Seções 4.3, 6 e 7 — composição dos riscos R1, R3, R4 e da frequência F.

O resultado nunca é só um número: 5.6.1 exige que o projetista veja a
contribuição de CADA componente para escolher a medida de proteção. Por isso
`Resultado` carrega a decomposição completa por zona, por linha e por
componente, que é o que alimenta o laudo e a tela de resultados.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import eventos as EV
from . import perdas as L
from . import probabilidades as P
from . import tabelas as T
from .modelo import Projeto, ZonaEstudo

# Componentes de R1, por fonte de dano (Tabela 6)
COMPONENTES_R1 = ("R_A", "R_B", "R_C", "R_M", "R_U", "R_V", "R_W", "R_Z")
COMPONENTES_R3 = ("R_B", "R_V")
COMPONENTES_R4 = ("R_A", "R_B", "R_C", "R_M", "R_U", "R_V", "R_W", "R_Z")
COMPONENTES_F = ("F_B", "F_C", "F_M", "F_V", "F_W", "F_Z")


@dataclass
class ResultadoZona:
    id_zona: str
    r1_componentes: dict[str, float] = field(default_factory=dict)
    r3_componentes: dict[str, float] = field(default_factory=dict)
    r4_componentes: dict[str, float] = field(default_factory=dict)
    f_componentes: dict[str, float] = field(default_factory=dict)
    p_c: float = 0.0
    p_m: float = 0.0

    @property
    def r1(self) -> float:
        return sum(self.r1_componentes.values())

    @property
    def r3(self) -> float:
        return sum(self.r3_componentes.values())

    @property
    def r4(self) -> float:
        return sum(self.r4_componentes.values())

    @property
    def f(self) -> float:
        return sum(self.f_componentes.values())


@dataclass
class Resultado:
    projeto: Projeto
    n_d: float
    n_m: float
    eventos_linhas: dict[str, EV.EventosLinha]
    zonas: list[ResultadoZona]

    inclui_falha_sistemas_em_r1: bool = False
    r3_aplicavel: bool = False
    r4_avaliado: bool = False

    # ------------------------------------------------------------------ somas
    @property
    def r1(self) -> float:
        return sum(z.r1 for z in self.zonas)

    @property
    def r3(self) -> float:
        return sum(z.r3 for z in self.zonas)

    @property
    def r4(self) -> float:
        return sum(z.r4 for z in self.zonas)

    @property
    def f(self) -> float:
        return sum(z.f for z in self.zonas)

    def componentes_r1(self) -> dict[str, float]:
        return {
            c: sum(z.r1_componentes.get(c, 0.0) for z in self.zonas)
            for c in COMPONENTES_R1
        }

    def componentes_r3(self) -> dict[str, float]:
        return {
            c: sum(z.r3_componentes.get(c, 0.0) for z in self.zonas)
            for c in COMPONENTES_R3
        }

    def componentes_r4(self) -> dict[str, float]:
        return {
            c: sum(z.r4_componentes.get(c, 0.0) for z in self.zonas)
            for c in COMPONENTES_R4
        }

    def componentes_f(self) -> dict[str, float]:
        return {
            c: sum(z.f_componentes.get(c, 0.0) for z in self.zonas)
            for c in COMPONENTES_F
        }

    # ---------------------------------------------------------------- limites
    @property
    def r_t_1(self) -> float:
        return T.R_T_R1

    @property
    def r_t_3(self) -> float:
        return T.R_T_R3

    @property
    def f_t(self) -> float:
        return self.projeto.f_t

    @property
    def r1_aprovado(self) -> bool:
        return self.r1 <= T.R_T_R1

    @property
    def r3_aprovado(self) -> bool | None:
        """None quando não há patrimônio cultural — 'não aplicável' não é
        'aprovado' (achado G-10)."""
        return None if not self.r3_aplicavel else self.r3 <= T.R_T_R3

    @property
    def f_aprovado(self) -> bool:
        return self.f <= self.f_t

    @property
    def r4_aprovado(self) -> bool | None:
        if not self.r4_avaliado:
            return None
        if self.projeto.modo_r4 == "representativo":
            return self.r4 <= T.R_T_R4
        return None  # modo detalhado: a decisão é econômica (D.2.3/D.2.4)

    @property
    def custo_anual_perda(self) -> float | None:
        """Eq. (D.8) — C_L = R4 × c_t, com c_t TOTAL da estrutura."""
        if not self.r4_avaliado or self.projeto.modo_r4 != "detalhado":
            return None
        return self.r4 * self.projeto.valor_total_estrutura

    @property
    def aprovado_geral(self) -> bool:
        ok = self.r1_aprovado and self.f_aprovado
        if self.r3_aplicavel:
            ok = ok and bool(self.r3_aprovado)
        return ok

    def maiores_contribuintes_r1(self, n: int = 3) -> list[tuple[str, float, float]]:
        """5.6.2 — parâmetros críticos. Retorna (componente, valor, % de R1)."""
        total = self.r1 or 1.0
        itens = sorted(
            self.componentes_r1().items(), key=lambda kv: kv[1], reverse=True
        )
        return [(c, v, 100.0 * v / total) for c, v in itens[:n] if v > 0]


# =============================================================================
# Motor
# =============================================================================
def analisar(projeto: Projeto) -> Resultado:
    est = projeto.estrutura
    nd = EV.n_d(projeto.n_g, est)
    nm = EV.n_m(projeto.n_g, est)
    ev_linhas = EV.eventos_das_linhas(projeto)
    linhas_por_id = {ln.id_linha: ln for ln in projeto.linhas}

    # Nota `a` da Tabela 2 / 4.3.1: derivada, nunca escolhida por checkbox.
    inclui_falha = projeto.falha_de_sistema_ameaca_vida
    r3_aplicavel = (
        any(L.zona_tem_patrimonio(z) for z in projeto.zonas)
        and projeto.valor_total_estrutura > 0
    )
    r4_avaliado = projeto.avaliar_r4 and (
        projeto.modo_r4 == "representativo" or projeto.valor_total_estrutura > 0
    )

    resultados: list[ResultadoZona] = []

    for zona in projeto.zonas:
        rz = ResultadoZona(id_zona=zona.id_zona)
        p_a = P.p_a(projeto, zona)
        p_b = P.p_b(projeto)
        p_c = P.p_c(zona, linhas_por_id)
        p_m = P.p_m(zona)
        rz.p_c, rz.p_m = p_c, p_m

        # ---------------- R1 — fontes S1 e S2 ----------------
        rz.r1_componentes["R_A"] = nd * p_a * L.l_a1(projeto, zona)
        rz.r1_componentes["R_B"] = nd * p_b * L.l_b1(projeto, zona)
        rz.r1_componentes["R_C"] = (
            nd * p_c * L.l_c1(projeto, zona) if inclui_falha else 0.0
        )
        rz.r1_componentes["R_M"] = (
            nm * p_m * L.l_m1(projeto, zona) if inclui_falha else 0.0
        )

        # ---------------- R3 — S1 ----------------
        rz.r3_componentes["R_B"] = nd * p_b * L.l_b3(projeto, zona)

        # ---------------- R4 — S1 e S2 ----------------
        if r4_avaliado:
            rz.r4_componentes["R_A"] = nd * p_a * L.l_a4(projeto, zona)
            rz.r4_componentes["R_B"] = nd * p_b * L.l_b4(projeto, zona)
            rz.r4_componentes["R_C"] = nd * p_c * L.l_c4(projeto, zona)
            rz.r4_componentes["R_M"] = nm * p_m * L.l_m4(projeto, zona)

        # ---------------- F — S1 e S2 (Tabela 7) ----------------
        # 7.1.5: F_B só entra se houver equipamento em ZPR0A.
        tem_zpr0a = any(s.em_zpr0a for s in zona.sistemas_internos)
        rz.f_componentes["F_B"] = nd * p_b if tem_zpr0a else 0.0
        rz.f_componentes["F_C"] = nd * p_c
        rz.f_componentes["F_M"] = nm * p_m

        # ---------------- fontes S3 e S4, por linha ----------------
        acc = {k: 0.0 for k in ("R_U", "R_V", "R_W", "R_Z")}
        acc4 = {k: 0.0 for k in ("R_U", "R_V", "R_W", "R_Z")}
        acc3_v = 0.0
        accf = {k: 0.0 for k in ("F_V", "F_W", "F_Z")}

        for ln in projeto.linhas:
            ev = ev_linhas[ln.id_linha]
            n_l_dj = ev.n_l_mais_n_dj
            p_u = P.p_u(projeto, zona, ln)
            p_v = P.p_v(projeto, zona, ln)
            p_w = P.p_w(zona, ln)
            p_z = P.p_z(zona, ln)

            acc["R_U"] += n_l_dj * p_u * L.l_u1(projeto, zona)
            acc["R_V"] += n_l_dj * p_v * L.l_v1(projeto, zona)
            if inclui_falha:
                acc["R_W"] += n_l_dj * p_w * L.l_w1(projeto, zona)
                acc["R_Z"] += ev.n_i * p_z * L.l_z1(projeto, zona)

            acc3_v += n_l_dj * p_v * L.l_v3(projeto, zona)

            if r4_avaliado:
                acc4["R_U"] += n_l_dj * p_u * L.l_u4(projeto, zona)
                acc4["R_V"] += n_l_dj * p_v * L.l_v4(projeto, zona)
                acc4["R_W"] += n_l_dj * p_w * L.l_w4(projeto, zona)
                acc4["R_Z"] += ev.n_i * p_z * L.l_z4(projeto, zona)

            # Tabela 7: F_V usa P_EB (e não P_V) — é a forma da edição 2026.
            accf["F_V"] += n_l_dj * projeto.p_eb
            accf["F_W"] += n_l_dj * p_w
            accf["F_Z"] += ev.n_i * p_z

        rz.r1_componentes.update(acc)
        rz.r3_componentes["R_V"] = acc3_v
        if r4_avaliado:
            rz.r4_componentes.update(acc4)
        rz.f_componentes.update(accf)

        resultados.append(rz)

    return Resultado(
        projeto=projeto,
        n_d=nd,
        n_m=nm,
        eventos_linhas=ev_linhas,
        zonas=resultados,
        inclui_falha_sistemas_em_r1=inclui_falha,
        r3_aplicavel=r3_aplicavel,
        r4_avaliado=r4_avaliado,
    )
