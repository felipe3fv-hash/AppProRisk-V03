"""Validação de consistência do projeto.

Regra do produto: um laudo só é emitido se não houver ERRO. Avisos não bloqueiam,
mas são impressos no laudo — o leitor precisa saber o que foi assumido.

Cada item cita a cláusula que o justifica. Isso é o que transforma a validação
de "polimento de interface" em parte do documento técnico.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import tabelas as T
from .modelo import Projeto


@dataclass(frozen=True)
class Item:
    nivel: str      # 'erro' | 'aviso'
    onde: str
    mensagem: str
    clausula: str = ""

    def __str__(self) -> str:
        c = f" [{self.clausula}]" if self.clausula else ""
        return f"{self.onde}: {self.mensagem}{c}"


def validar(projeto: Projeto) -> list[Item]:
    it: list[Item] = []
    E = lambda o, m, c="": it.append(Item("erro", o, m, c))       # noqa: E731
    A = lambda o, m, c="": it.append(Item("aviso", o, m, c))      # noqa: E731

    # ------------------------------------------------------------ localidade
    if projeto.n_g <= 0:
        E("Localidade", "N_G não definido. Selecione o município (Anexo F).", "A.1.3")
    if projeto.n_g_sobrescrito and not projeto.n_g_justificativa.strip():
        E(
            "Localidade",
            "N_G foi sobrescrito manualmente sem justificativa. A norma admite "
            "apenas os valores do Anexo F; qualquer desvio precisa ser "
            "justificado e imposto por autoridade com jurisdição.",
            "A.1.3 / F.1.1",
        )
    if projeto.n_g_sobrescrito:
        A("Localidade", "N_G sobrescrito manualmente — registrado no laudo.", "A.1.3")

    # ------------------------------------------------------------- estrutura
    est = projeto.estrutura
    if est.a_d_informada_m2 is not None:
        if est.a_d_informada_m2 <= 0:
            E("Estrutura", "A_D informada deve ser maior que zero.", "A.2.1")
        if not est.a_d_justificativa.strip():
            E(
                "Estrutura",
                "A_D determinada graficamente exige descrição do método adotado.",
                "A.2.1.3.1",
            )
    else:
        if est.comprimento_m <= 0 or est.largura_m <= 0:
            E("Estrutura", "Comprimento e largura devem ser maiores que zero.", "A.2.1.2")
        if est.altura_m <= 0:
            E("Estrutura", "Altura da estrutura deve ser maior que zero.", "A.2.1.2")
    if est.altura_saliencia_m and est.altura_saliencia_m < est.altura_m:
        A(
            "Estrutura",
            "Altura da saliência menor que a do corpo principal — A_D será "
            "determinada apenas pela eq. (A.1).",
            "A.2.1.3.2",
        )

    # ----------------------------------------------------------------- zonas
    if not projeto.zonas:
        E("Zonas", "Cadastre ao menos uma zona de estudo.", "6.7.1")

    soma_nz = sum(z.pessoas_na_zona for z in projeto.zonas)
    if projeto.pessoas_total <= 0:
        E("Pessoas", "Número total de pessoas na estrutura (n_t) deve ser maior que zero.", "C.3.1 b")
    elif soma_nz > projeto.pessoas_total + 1e-9:
        E(
            "Pessoas",
            f"A soma das pessoas por zona ({soma_nz:g}) excede o total da "
            f"estrutura n_t ({projeto.pessoas_total:g}).",
            "C.3.1 b",
        )
    elif soma_nz < projeto.pessoas_total - 1e-9:
        A(
            "Pessoas",
            f"A soma das pessoas por zona ({soma_nz:g}) é menor que n_t "
            f"({projeto.pessoas_total:g}). Confirme se há áreas não zoneadas.",
            "6.9.3.1",
        )

    ids_zona = [z.id_zona for z in projeto.zonas]
    if len(set(ids_zona)) != len(ids_zona):
        E("Zonas", "Há zonas com identificadores repetidos.")

    for z in projeto.zonas:
        onde = f"Zona '{z.id_zona}'"
        if z.pessoas_na_zona < 0:
            E(onde, "Número de pessoas não pode ser negativo.")
        if not (0 <= z.horas_presenca_ano <= 8760):
            E(onde, "Tempo de presença t_z deve estar entre 0 e 8 760 h/ano.", "C.3.1 c")
        if not z.sistemas_internos:
            E(
                onde,
                "Declare ao menos um sistema interno. P_C, P_M, P_LD e P_LI "
                "dependem do U_W do equipamento a proteger.",
                "6.9.1.2 b / B.4.15",
            )
        if z.risco_de_explosao and z.r_p_chave != "nenhuma":
            A(
                onde,
                "Estrutura com risco de explosão: r_p foi forçado a 1,00 "
                "independentemente da providência selecionada.",
                "C.3.4",
            )
        if z.r_f_chave == "nenhum" and z.perdas["L_F_L1"] > 0:
            A(
                onde,
                "r_f = 0 zera R_B e R_V. Confirme que não há risco de incêndio "
                "nem de explosão na zona.",
                "Tabela C.5",
            )
        for s in z.sistemas_internos:
            o2 = f"{onde} / sistema '{s.id_sistema}'"
            if s.uw_kv <= 0:
                E(o2, "U_W deve ser maior que zero.", "B.4.14")
            elif s.uw_kv not in T.UW_COLUNAS_PLD:
                A(
                    o2,
                    f"U_W = {s.uw_kv} kV não é valor tabelado. Foi adotada a "
                    "coluna tabelada imediatamente inferior (conservador).",
                    "Tabela B.8",
                )
            if not s.sistema_independente and not s.ids_linhas:
                E(
                    o2,
                    "Sistema não é independente e não foi vinculado a nenhuma "
                    "linha elétrica. Vincule as linhas ou marque-o como "
                    "sistema independente.",
                    "Tabela B.4",
                )
            faltantes = [i for i in s.ids_linhas if i not in {l.id_linha for l in projeto.linhas}]
            if faltantes:
                E(o2, f"Linhas vinculadas inexistentes: {', '.join(faltantes)}.")
            if not s.atende_normas_de_produto:
                A(
                    o2,
                    "Equipamento não atende às normas de produto quanto a U_W: "
                    "P_M foi fixado em 1,00.",
                    "B.4.10",
                )

    # ---------------------------------------------------------------- linhas
    if not projeto.linhas:
        A(
            "Linhas",
            "Nenhuma linha elétrica cadastrada. R_U, R_V, R_W e R_Z serão nulos. "
            "Confirme que a estrutura é eletricamente independente.",
            "6.4 / Tabela B.4",
        )
    ids_linha = [l.id_linha for l in projeto.linhas]
    if len(set(ids_linha)) != len(ids_linha):
        E("Linhas", "Há linhas com identificadores repetidos.")

    for ln in projeto.linhas:
        onde = f"Linha '{ln.id_linha}'"
        if not ln.trechos:
            E(onde, "Cadastre ao menos um trecho.", "6.8.1")
        for t in ln.trechos:
            if t.comprimento_m <= 0:
                E(f"{onde} / {t.id_trecho}", "Comprimento L_L deve ser maior que zero.", "A.4.1")
            if t.c_i_chave == "aereo" and t.resistividade_solo_ohm_m != 400.0:
                A(
                    f"{onde} / {t.id_trecho}",
                    "Resistividade do solo é irrelevante em trecho aéreo e foi ignorada.",
                    "Nota 1 da Tabela A.2",
                )
        if ln.blindada and not ln.blindagem_no_mesmo_bep:
            A(
                onde,
                "Blindagem não interligada ao mesmo BEP do equipamento: "
                "P_LD = 1,00, ou seja, a blindagem não é creditada.",
                "Tabela B.8",
            )
        if ln.blindada and ln.blindagem_no_mesmo_bep and ln.resistencia_blindagem_ohm_km > 20:
            A(
                onde,
                f"R_S = {ln.resistencia_blindagem_ohm_km:g} Ω/km está acima da "
                "maior faixa tabelada (20 Ω/km): P_LD = 1,00.",
                "Tabela B.8",
            )
        if not ln.blindada and ln.blindagem_no_mesmo_bep:
            E(onde, "Blindagem interligada ao BEP marcada em linha não blindada.")
        if ln.neutro_multiaterrado and ln.tipo != "energia":
            E(onde, "Neutro multiaterrado só se aplica a linha de energia.", "Tabela B.4")
        if ln.interface_isolante and not ln.interface_isolante_protegida_por_dps:
            A(
                onde,
                "Interface isolante sem DPS de proteção: C_LD = 1,00 conforme a "
                "nota `a` da Tabela B.4 (apenas C_LI = 0).",
                "Nota a da Tabela B.4",
            )
        adj = ln.estrutura_adjacente
        if adj and (adj.comprimento_m <= 0 or adj.largura_m <= 0 or adj.altura_m <= 0):
            E(f"{onde} / adjacente", "Dimensões da estrutura adjacente devem ser positivas.", "A.2.5")

    # -------------------------------------------------------------- Anexo D
    if projeto.avaliar_r4:
        c_t = projeto.valor_total_estrutura
        if projeto.modo_r4 == "detalhado":
            if c_t <= 0:
                E(
                    "Anexo D",
                    "Avaliação detalhada de R4 exige o valor total da estrutura "
                    "c_t maior que zero.",
                    "D.1.3 / D.4",
                )
            else:
                soma = sum(
                    z.valor_animais + z.valor_edificacao + z.valor_conteudo + z.valor_sistemas
                    for z in projeto.zonas
                )
                if soma > c_t * 1.000001:
                    E(
                        "Anexo D",
                        f"A soma dos valores das zonas (R$ {soma:,.2f}) excede o "
                        f"valor total da estrutura c_t (R$ {c_t:,.2f}).",
                        "D.3.1 b",
                    )
                elif soma < c_t * 0.999999:
                    A(
                        "Anexo D",
                        f"A soma dos valores das zonas (R$ {soma:,.2f}) é menor "
                        f"que c_t (R$ {c_t:,.2f}).",
                        "D.3.1 b",
                    )
        else:
            A(
                "Anexo D",
                "Modo representativo: as razões c_x/c_t foram substituídas por 1 "
                "e R4 é comparado com R_T = 1×10⁻³.",
                "Nota a da Tabela D.1 / D.1.2",
            )

    # ------------------------------------------------------ patrimônio / R3
    if any(z.valor_patrimonio_cultural > 0 for z in projeto.zonas):
        if projeto.valor_total_estrutura <= 0:
            E(
                "R3",
                "Há patrimônio cultural declarado (c_z > 0), mas c_t não foi "
                "informado. L_B3 depende de c_z/c_t.",
                "C.4.1 b",
            )

    # --------------------------------------------------- frequência de danos
    if not projeto.sistema_critico:
        A(
            "Frequência de danos",
            "Sistema declarado como NÃO crítico: F_T = 1,0/ano, valor meramente "
            "representativo. Para sistema crítico F_T = 0,1/ano e não pode ser "
            "alterado.",
            "7.3.3 / 7.3.4",
        )
    if not any(s.em_zpr0a for z in projeto.zonas for s in z.sistemas_internos):
        A(
            "Frequência de danos",
            "Nenhum equipamento declarado em ZPR0A: F_B foi adotado igual a zero.",
            "7.1.5",
        )

    # ---------------------------------------------------- responsável técnico
    ident = projeto.identificacao
    if not ident.responsavel_tecnico.strip() or not ident.crea.strip():
        A(
            "Identificação",
            "Responsável técnico e registro CREA não preenchidos — o laudo sairá "
            "sem identificação profissional.",
        )

    return it


def tem_erro(itens: list[Item]) -> bool:
    return any(i.nivel == "erro" for i in itens)


def erros(itens: list[Item]) -> list[Item]:
    return [i for i in itens if i.nivel == "erro"]


def avisos(itens: list[Item]) -> list[Item]:
    return [i for i in itens if i.nivel == "aviso"]
