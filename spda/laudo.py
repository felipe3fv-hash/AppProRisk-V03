"""Emissão do laudo técnico em PDF (A4).

Um laudo de análise de risco tem que ser REPRODUTÍVEL por terceiros. Por isso
ele contém, além do veredito:

  · identificação do responsável técnico, CREA e ART;
  · memorial completo dos dados de entrada (5.4.2 exige a identificação dos
    componentes e dos parâmetros usados);
  · decomposição por componente com participação percentual, sem a qual 5.6.1
    e 5.6.2 não podem ser cumpridos;
  · N_D, N_M, N_L, N_I, N_DJ e A_D, que permitem refazer o cálculo à mão;
  · versão do motor, norma aplicada e hash SHA-256 dos dados de entrada.
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from . import tabelas as T
from .analise import Resultado
from .modelo import Projeto
from .projeto_io import impressao_digital
from .validacao import avisos as _avisos
from .versao import NOME_PRODUTO, NORMA_APLICADA, VERSAO_MOTOR

AZUL = colors.HexColor("#1B4F72")
CINZA = colors.HexColor("#5A6472")
LINHA = colors.HexColor("#BDC3C7")
FUNDO = colors.HexColor("#F2F4F6")
VERDE = colors.HexColor("#1E6F42")
VERMELHO = colors.HexColor("#9B1C1C")

_ss = getSampleStyleSheet()
EST = {
    "titulo": ParagraphStyle("t", parent=_ss["Heading1"], fontName="Helvetica-Bold",
                             fontSize=15, textColor=AZUL, spaceAfter=2, leading=18),
    "sub": ParagraphStyle("s", parent=_ss["Normal"], fontSize=9, textColor=CINZA, spaceAfter=10),
    "h2": ParagraphStyle("h2", parent=_ss["Heading2"], fontName="Helvetica-Bold",
                         fontSize=11, textColor=AZUL, spaceBefore=12, spaceAfter=6),
    "h3": ParagraphStyle("h3", parent=_ss["Normal"], fontName="Helvetica-Bold",
                         fontSize=9.5, spaceBefore=8, spaceAfter=3),
    "p": ParagraphStyle("p", parent=_ss["Normal"], fontSize=8.8, leading=12,
                        alignment=TA_JUSTIFY, spaceAfter=5),
    "nota": ParagraphStyle("n", parent=_ss["Normal"], fontSize=7.6, leading=10,
                           textColor=CINZA, spaceAfter=4),
    "cel": ParagraphStyle("c", parent=_ss["Normal"], fontSize=7.8, leading=10),
    "assin": ParagraphStyle("a", parent=_ss["Normal"], fontSize=9, alignment=TA_CENTER),
}


def _fmt(v: float, casas: int = 2) -> str:
    return f"{v:.{casas}e}"


def _brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")


def _tabela(dados, larguras, cabecalho=True, alinhar_num=True, estilo_extra=None):
    t = Table(dados, colWidths=larguras, repeatRows=1 if cabecalho else 0)
    cmds = [
        ("GRID", (0, 0), (-1, -1), 0.4, LINHA),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if cabecalho:
        cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), AZUL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
        if alinhar_num:
            cmds.append(("ALIGN", (1, 1), (-1, -1), "RIGHT"))
    t.setStyle(TableStyle(cmds + (estilo_extra or [])))
    return t


def _campos(pares, larg=(45 * mm, 130 * mm)):
    dados = [[Paragraph(f"<b>{k}</b>", EST["cel"]), Paragraph(str(v), EST["cel"])] for k, v in pares]
    t = Table(dados, colWidths=larg)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, LINHA),
        ("BACKGROUND", (0, 0), (0, -1), FUNDO),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


# =============================================================================
def gerar_laudo(
    projeto: Projeto,
    resultado: Resultado,
    itens_validacao: list | None = None,
) -> bytes:
    buf = io.BytesIO()
    hash_dados = impressao_digital(projeto)
    emissao = projeto.identificacao.data_emissao or datetime.now().strftime("%d/%m/%Y")

    def rodape(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(LINHA)
        canvas.setLineWidth(0.4)
        canvas.line(18 * mm, 15 * mm, A4[0] - 18 * mm, 15 * mm)
        canvas.setFont("Helvetica", 6.6)
        canvas.setFillColor(CINZA)
        canvas.drawString(
            18 * mm, 11 * mm,
            f"{NOME_PRODUTO} v{VERSAO_MOTOR} · {NORMA_APLICADA} · "
            f"impressão digital dos dados: {hash_dados[:16]}",
        )
        canvas.drawRightString(A4[0] - 18 * mm, 11 * mm, f"Página {doc.page}")
        canvas.restoreState()

    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=20 * mm,
        title=f"Laudo de análise de risco — {projeto.identificacao.obra or 'SPDA'}",
        author=projeto.identificacao.responsavel_tecnico or NOME_PRODUTO,
        subject=NORMA_APLICADA,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=rodape)])

    el: list = []
    A = el.append

    # ---------------------------------------------------------------- capa
    A(Paragraph("LAUDO TÉCNICO DE ANÁLISE DE RISCO CONTRA DESCARGAS ATMOSFÉRICAS", EST["titulo"]))
    A(Paragraph(f"Norma de referência: {NORMA_APLICADA}", EST["sub"]))

    ident = projeto.identificacao
    A(Paragraph("1. Identificação", EST["h2"]))
    A(_campos([
        ("Obra / edificação", ident.obra or "—"),
        ("Endereço", ident.endereco or "—"),
        ("Proprietário", ident.proprietario or "—"),
        ("Responsável técnico", ident.responsavel_tecnico or "—"),
        ("Registro CREA", ident.crea or "—"),
        ("ART", ident.art or "—"),
        ("Data de emissão", emissao),
    ]))

    # ------------------------------------------------------------ localidade
    A(Paragraph("2. Atividade atmosférica (Anexo F)", EST["h2"]))
    origem = (
        "Sobrescrito manualmente — ver justificativa"
        if projeto.n_g_sobrescrito
        else "Tabela F.1 do Anexo F (valor por município)"
    )
    pares = [
        ("Município / UF", f"{projeto.municipio or '—'} / {projeto.uf or '—'}"),
        ("N<sub>G</sub> adotado", f"{projeto.n_g:g} raios/km<super>2</super>/ano"),
        ("Origem do valor", origem),
    ]
    if projeto.n_g_sobrescrito:
        pares.append(("Justificativa", projeto.n_g_justificativa or "—"))
    A(_campos(pares))
    A(Paragraph(
        "A.1.3 e F.1.1 determinam que os valores de N<sub>G</sub> sejam os do Anexo F, "
        "sendo vedado o uso de dados de outras fontes.", EST["nota"]))

    # ---------------------------------------------------------- síntese
    A(Paragraph("3. Síntese dos riscos e veredito", EST["h2"]))

    def veredito(ok):
        if ok is None:
            return "NÃO APLICÁVEL"
        return "ATENDE" if ok else "NÃO ATENDE — exigem-se medidas de proteção"

    linhas_sintese = [
        ["Grandeza", "Valor calculado", "Limite", "Referência", "Veredito"],
        ["R1 — perda de vida humana", _fmt(resultado.r1), _fmt(T.R_T_R1),
         "Tabela 4", veredito(resultado.r1_aprovado)],
        ["R3 — perda de patrimônio cultural",
         _fmt(resultado.r3) if resultado.r3_aplicavel else "—",
         _fmt(T.R_T_R3), "Tabela 4", veredito(resultado.r3_aprovado)],
        ["F — frequência de danos", f"{resultado.f:.4f} /ano",
         f"{resultado.f_t:.1f} /ano",
         "7.3.4 " + ("(sistema crítico)" if projeto.sistema_critico else "(não crítico)"),
         veredito(resultado.f_aprovado)],
    ]
    if resultado.r4_avaliado:
        if projeto.modo_r4 == "representativo":
            linhas_sintese.append(
                ["R4 — perda de valor econômico", _fmt(resultado.r4), _fmt(T.R_T_R4),
                 "D.1.2 (informativo)", veredito(resultado.r4_aprovado)]
            )
        else:
            linhas_sintese.append(
                ["R4 — perda de valor econômico", _fmt(resultado.r4),
                 "análise custo-benefício", "Anexo D (informativo)",
                 f"C_L = {_brl(resultado.custo_anual_perda or 0.0)}/ano"]
            )

    def _cor_veredito(txt: str) -> str:
        if txt.startswith("NÃO ATENDE"):
            return f'<font color="#9B1C1C"><b>{txt}</b></font>'
        if txt == "ATENDE":
            return f'<font color="#1E6F42"><b>{txt}</b></font>'
        return txt

    linhas_sintese = [linhas_sintese[0]] + [
        [Paragraph(c if i != 4 else _cor_veredito(c), EST["cel"]) for i, c in enumerate(ln)]
        for ln in linhas_sintese[1:]
    ]
    estilo = []
    A(_tabela(linhas_sintese, [46 * mm, 26 * mm, 24 * mm, 30 * mm, 48 * mm],
              alinhar_num=False, estilo_extra=estilo))

    conclusao = (
        "Os riscos avaliados encontram-se abaixo dos valores toleráveis. Conforme 5.4.3, "
        "os resultados são suficientes, ressalvadas eventuais exigências decorrentes da "
        "frequência de danos."
        if resultado.aprovado_geral else
        "Ao menos um dos riscos avaliados supera o valor tolerável. Conforme 5.4.4, medidas "
        "de proteção devem ser adotadas até que a condição R ≤ R_T seja satisfeita para todos "
        "os tipos de risco a que a estrutura está sujeita."
    )
    A(Spacer(1, 5))
    A(Paragraph(f"<b>Conclusão.</b> {conclusao}", EST["p"]))

    if not resultado.inclui_falha_sistemas_em_r1:
        A(Paragraph(
            "As componentes R<sub>C</sub>, R<sub>M</sub>, R<sub>W</sub> e R<sub>Z</sub> não compõem R1 neste caso, por não se "
            "tratar de estrutura com risco de explosão nem de estrutura em que a falha de "
            "sistemas internos possa colocar em risco imediato a vida humana (nota <i>a</i> da Tabela 2).",
            EST["nota"]))
    else:
        A(Paragraph(
            "As componentes R<sub>C</sub>, R<sub>M</sub>, R<sub>W</sub> e R<sub>Z</sub> compõem R1, por força da nota <i>a</i> da "
            "Tabela 2 (risco de explosão ou falha de sistemas internos com ameaça imediata à vida).",
            EST["nota"]))

    # ------------------------------------------- componentes e criticidade
    A(PageBreak())
    A(Paragraph("4. Decomposição por componente de risco", EST["h2"]))
    A(Paragraph(
        "5.6.1 determina que a seleção das medidas de proteção considere a contribuição de "
        "cada componente para o risco total, e 5.6.2 exige a identificação dos parâmetros "
        "críticos. A tabela abaixo é o insumo dessa decisão.", EST["p"]))

    comp_r1 = resultado.componentes_r1()
    total_r1 = resultado.r1 or 1.0
    fontes = {
        "R_A": "S1 — descarga na estrutura", "R_B": "S1 — descarga na estrutura",
        "R_C": "S1 — descarga na estrutura", "R_M": "S2 — descarga próximo da estrutura",
        "R_U": "S3 — descarga na linha", "R_V": "S3 — descarga na linha",
        "R_W": "S3 — descarga na linha", "R_Z": "S4 — descarga próximo da linha",
    }
    danos = {
        "R_A": "D1 — ferimentos por choque", "R_B": "D2 — danos físicos",
        "R_C": "D3 — falha de sistemas internos", "R_M": "D3 — falha de sistemas internos",
        "R_U": "D1 — ferimentos por choque", "R_V": "D2 — danos físicos",
        "R_W": "D3 — falha de sistemas internos", "R_Z": "D3 — falha de sistemas internos",
    }
    dados = [["Componente", "Fonte de dano", "Tipo de dano", "Valor (1/ano)", "% de R1"]]
    for c in ("R_A", "R_B", "R_C", "R_M", "R_U", "R_V", "R_W", "R_Z"):
        v = comp_r1.get(c, 0.0)
        dados.append([c.replace("_", ""), fontes[c], danos[c], _fmt(v), f"{100 * v / total_r1:.1f} %"])
    dados.append(["R1", "", "", _fmt(resultado.r1), "100,0 %"])
    A(_tabela(dados, [20 * mm, 48 * mm, 46 * mm, 30 * mm, 20 * mm], alinhar_num=False,
              estilo_extra=[
                  ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
                  ("BACKGROUND", (0, len(dados) - 1), (-1, len(dados) - 1), FUNDO),
                  ("FONTNAME", (0, len(dados) - 1), (-1, len(dados) - 1), "Helvetica-Bold"),
              ]))

    maiores = resultado.maiores_contribuintes_r1(3)
    if maiores:
        txt = "; ".join(f"{c.replace('_','')} ({p:.1f} %)" for c, _, p in maiores)
        A(Paragraph(f"<b>Parâmetros críticos (5.6.2).</b> Maiores contribuintes para R1: {txt}.", EST["p"]))

    # --- frequência de danos
    sub = 1
    A(Paragraph(f"4.{sub}. Frequência parcial de danos (Tabela 7)", EST["h3"]))
    cf = resultado.componentes_f()
    dados_f = [["Componente", "Equação", "Valor (1/ano)"]]
    eqs = {
        "F_B": "F_B = N_D × P_B  (só equipamento em ZPR0A — 7.1.5)",
        "F_C": "F_C = N_D × P_C",
        "F_M": "F_M = N_M × P_M",
        "F_V": "F_V = (N_L + N_DJ) × P_EB",
        "F_W": "F_W = (N_L + N_DJ) × P_W",
        "F_Z": "F_Z = N_I × P_Z",
    }
    for c in ("F_B", "F_C", "F_M", "F_V", "F_W", "F_Z"):
        dados_f.append([c.replace("_", ""), eqs[c], f"{cf.get(c, 0.0):.5f}"])
    dados_f.append(["F", "soma (eq. 14)", f"{resultado.f:.5f}"])
    A(_tabela(dados_f, [20 * mm, 114 * mm, 30 * mm], alinhar_num=False,
              estilo_extra=[
                  ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                  ("BACKGROUND", (0, len(dados_f) - 1), (-1, len(dados_f) - 1), FUNDO),
                  ("FONTNAME", (0, len(dados_f) - 1), (-1, len(dados_f) - 1), "Helvetica-Bold"),
              ]))

    if resultado.r3_aplicavel:
        sub += 1
        A(Paragraph(f"4.{sub}. Componentes de R3", EST["h3"]))
        c3 = resultado.componentes_r3()
        A(_tabela([["Componente", "Valor (1/ano)"],
                   ["RB3", _fmt(c3.get("R_B", 0.0))],
                   ["RV3", _fmt(c3.get("R_V", 0.0))],
                   ["R3", _fmt(resultado.r3)]],
                  [40 * mm, 40 * mm]))

    if resultado.r4_avaliado:
        sub += 1
        A(Paragraph(f"4.{sub}. Componentes de R4 (Anexo D — informativo)", EST["h3"]))
        c4 = resultado.componentes_r4()
        d4 = [["Componente", "Valor (1/ano)"]]
        for c in ("R_A", "R_B", "R_C", "R_M", "R_U", "R_V", "R_W", "R_Z"):
            d4.append([c.replace("_", "") + "4", _fmt(c4.get(c, 0.0))])
        d4.append(["R4", _fmt(resultado.r4)])
        A(_tabela(d4, [40 * mm, 40 * mm]))

    # -------------------------------------------------- memorial de entrada
    A(PageBreak())
    A(Paragraph("5. Memorial dos dados de entrada", EST["h2"]))
    A(Paragraph(
        "Reproduzido integralmente para que a análise possa ser refeita e conferida por "
        "terceiros a partir deste documento.", EST["p"]))

    est = projeto.estrutura
    A(Paragraph("5.1. Estrutura", EST["h3"]))
    geo = [
        ("Comprimento L", f"{est.comprimento_m:g} m"),
        ("Largura W", f"{est.largura_m:g} m"),
        ("Altura H", f"{est.altura_m:g} m"),
        ("Altura da saliência H<sub>P</sub>", f"{est.altura_saliencia_m:g} m"),
        ("Fator de localização C<sub>D</sub>", f"{est.c_d:g} — {T.rotulo(T.C_D, est.c_d_chave)}"),
        ("Área de exposição A<sub>D</sub>", f"{est.a_d():,.1f} m<super>2</super>"
            + (" (determinada graficamente)" if est.a_d_informada_m2 is not None else " — eq. (A.1)/(A.2)")),
        ("Área de exposição A<sub>M</sub>", f"{est.a_m():,.1f} m<super>2</super> — eq. (A.6)"),
        ("SPDA externo (P<sub>B</sub>)", f"{projeto.p_b:g} — {T.rotulo(T.P_B, projeto.p_b_chave)}"),
        ("DPS classe I na entrada (P<sub>EB</sub>)", f"{projeto.p_eb:g} — {T.rotulo(T.P_EB, projeto.p_eb_chave)}"),
        ("Total de pessoas n<sub>t</sub>", f"{projeto.pessoas_total:g}"),
        ("Sistema crítico (7.3.3)", "sim — F_T = 0,1/ano" if projeto.sistema_critico else "não — F_T = 1,0/ano"),
    ]
    if est.a_d_informada_m2 is not None:
        geo.append(("Método gráfico — descrição", est.a_d_justificativa or "—"))
    A(_campos(geo))

    A(Paragraph("5.2. Eventos perigosos (Anexo A)", EST["h3"]))
    dn = [["Grandeza", "Valor (1/ano)", "Equação"],
          ["N_D", f"{resultado.n_d:.5e}", "A.3"],
          ["N_M", f"{resultado.n_m:.5e}", "A.5"]]
    for ln in projeto.linhas:
        ev = resultado.eventos_linhas[ln.id_linha]
        dn.append([f"N_L — {ln.id_linha}", f"{ev.n_l:.5e}", "A.7"])
        dn.append([f"N_I — {ln.id_linha}", f"{ev.n_i:.5e}", "A.9"])
        dn.append([f"N_DJ — {ln.id_linha}", f"{ev.n_dj:.5e}", "A.4"])
    A(_tabela(dn, [70 * mm, 45 * mm, 25 * mm], alinhar_num=False,
              estilo_extra=[("ALIGN", (1, 1), (1, -1), "RIGHT")]))

    A(Paragraph("5.3. Zonas de estudo", EST["h3"]))
    for z, rz in zip(projeto.zonas, resultado.zonas):
        pares = [
            ("Ocupação", z.perdas["rotulo"]),
            ("Pessoas na zona n<sub>z</sub> / tempo t<sub>z</sub>",
             f"{z.pessoas_na_zona:g} pessoas · {z.horas_presenca_ano:g} h/ano"),
            ("r<sub>t</sub> (Tabela C.3)", f"{z.r_t:g} — {T.rotulo(T.R_T, z.r_t_chave)}"),
            ("r<sub>p</sub> (Tabela C.4)", f"{z.r_p:g} — "
                + ("forçado a 1 por risco de explosão (C.3.4)" if z.risco_de_explosao
                   else T.rotulo(T.R_P, z.r_p_chave))),
            ("r<sub>f</sub> (Tabela C.5)", f"{z.r_f:g} — {T.rotulo(T.R_F, z.r_f_chave)}"),
            ("h<sub>z</sub> (Tabela C.6)", f"{z.h_z:g} — {T.rotulo(T.H_Z, z.h_z_chave)}"),
            ("r<sub>s</sub> (Tabela C.7)", f"{z.r_s:g} — {T.rotulo(T.R_S_CONSTRUCAO, z.r_s_chave)}"),
            ("P<sub>TA</sub> (Tabela B.1)", f"{z.p_ta:g} — "
                + "; ".join(T.rotulo(T.P_TA, c) for c in z.p_ta_chaves)),
            ("P<sub>TU</sub> (Tabela B.6)", f"{z.p_tu:g} — "
                + "; ".join(T.rotulo(T.P_TU, c) for c in z.p_tu_chaves)),
            ("K<sub>S1</sub> / K<sub>S2</sub> (B.4.12)", f"{z.k_s1():g} / {z.k_s2():g}"),
            ("L<sub>F</sub> · L<sub>O</sub> para L1 (Tabela C.2)",
             f"{z.perdas['L_F_L1']:g} · {z.perdas['L_O_L1']:g}"),
            ("L<sub>F</sub> para L3 (Tabela C.9)", f"{z.perdas['L_F_L3']:g}"),
            ("L<sub>F</sub> · L<sub>O</sub> para L4 (Tabela D.2)",
             f"{z.perdas['L_F_L4']:g} · {z.perdas['L_O_L4']:g}"),
            ("P<sub>C</sub> · P<sub>M</sub> compostos (eq. 12 e 13)", f"{rz.p_c:.4g} · {rz.p_m:.4g}"),
        ]
        if resultado.r4_avaliado or z.valor_patrimonio_cultural:
            pares.append(("Valores c<sub>a</sub>/c<sub>b</sub>/c<sub>c</sub>/c<sub>s</sub>/c<sub>z</sub>",
                          " · ".join(_brl(v) for v in (z.valor_animais, z.valor_edificacao,
                                                       z.valor_conteudo, z.valor_sistemas,
                                                       z.valor_patrimonio_cultural))))
        bloco = [Paragraph(f"Zona: <b>{z.id_zona}</b>", EST["cel"]), Spacer(1, 2), _campos(pares)]
        if z.sistemas_internos:
            ds = [["Sistema interno", "U_W (kV)", "P_SPD", "K_S3", "Blindado", "ZPR0A", "Linhas"]]
            for s in z.sistemas_internos:
                ds.append([s.id_sistema, f"{s.uw_kv:g}", f"{s.p_spd:g}", f"{s.k_s3:g}",
                           "sim" if s.blindado else "não",
                           "sim" if s.em_zpr0a else "não",
                           ", ".join(s.ids_linhas) or "independente"])
            bloco += [Spacer(1, 3), _tabela(ds, [32 * mm, 16 * mm, 16 * mm, 16 * mm,
                                                 16 * mm, 14 * mm, 44 * mm],
                                            alinhar_num=False)]
        bloco.append(Spacer(1, 8))
        A(KeepTogether(bloco))

    A(Paragraph("5.4. Linhas elétricas", EST["h3"]))
    for ln in projeto.linhas:
        c_ld, c_li = ln.c_ld_c_li()
        pares = [
            ("Tipo", "energia" if ln.tipo == "energia" else "sinal"),
            ("Blindagem", ("blindada, R_S = %g Ω/km, %s ao mesmo BEP" % (
                ln.resistencia_blindagem_ohm_km,
                "interligada" if ln.blindagem_no_mesmo_bep else "NÃO interligada"))
                if ln.blindada else "não blindada"),
            ("Faixa da Tabela B.8", ln.faixa_p_ld.replace("_", " ")),
            ("C<sub>LD</sub> / C<sub>LI</sub> (Tabela B.4)", f"{c_ld:g} / {c_li:g}"),
            ("Neutro multiaterrado", "sim" if ln.neutro_multiaterrado else "não"),
            ("Interface isolante", ("sim, " + ("com DPS" if ln.interface_isolante_protegida_por_dps
                                               else "sem DPS")) if ln.interface_isolante else "não"),
            ("Eletroduto/cabo de proteção metálico", "sim" if ln.cabo_protecao_ou_conduto_metalico else "não"),
        ]
        dt = [["Trecho", "L_L (m)", "C_I", "C_E", "C_T", "ρ (Ω·m)"]]
        for t in ln.trechos:
            dt.append([t.id_trecho, f"{t.comprimento_m:g}", f"{t.c_i:g}", f"{t.c_e:g}",
                       f"{t.c_t:g}", f"{t.resistividade_solo_ohm_m:g}" if t.enterrado else "—"])
        bloco = [Paragraph(f"Linha: <b>{ln.id_linha}</b>", EST["cel"]), Spacer(1, 2),
                 _campos(pares), Spacer(1, 3),
                 _tabela(dt, [46 * mm, 26 * mm, 20 * mm, 20 * mm, 20 * mm, 22 * mm],
                         alinhar_num=False)]
        if ln.estrutura_adjacente:
            adj = ln.estrutura_adjacente
            bloco += [Spacer(1, 3), _campos([
                ("Estrutura adjacente", f"{adj.comprimento_m:g} × {adj.largura_m:g} × {adj.altura_m:g} m"),
                ("C<sub>DJ</sub>", f"{adj.c_dj:g} — {T.rotulo(T.C_D, adj.c_dj_chave)}"),
                ("A<sub>DJ</sub>", f"{adj.a_dj():,.1f} m<super>2</super>"),
            ])]
        bloco.append(Spacer(1, 8))
        A(KeepTogether(bloco))

    # ------------------------------------------------------------- ressalvas
    avisos = _avisos(itens_validacao or [])
    if avisos:
        A(Paragraph("6. Ressalvas e premissas assumidas", EST["h2"]))
        A(Paragraph(
            "Registradas automaticamente pelo sistema durante a validação dos dados de "
            "entrada. Não impedem a emissão, mas integram o laudo.", EST["p"]))
        d = [["Onde", "Premissa / ressalva", "Cláusula"]]
        for a in avisos:
            d.append([Paragraph(a.onde, EST["cel"]),
                      Paragraph(a.mensagem, EST["cel"]),
                      Paragraph(a.clausula or "—", EST["cel"])])
        A(_tabela(d, [30 * mm, 108 * mm, 26 * mm], alinhar_num=False))

    if projeto.observacoes.strip():
        A(Paragraph("7. Observações do responsável técnico", EST["h2"]))
        A(Paragraph(projeto.observacoes.replace("\n", "<br/>"), EST["p"]))

    # ------------------------------------------------------------ assinatura
    A(Spacer(1, 22))
    A(Paragraph("_" * 58, EST["assin"]))
    A(Paragraph(f"<b>{ident.responsavel_tecnico or 'Responsável técnico'}</b>", EST["assin"]))
    A(Paragraph(
        f"Engenheiro Eletricista — CREA {ident.crea or '—'} · ART {ident.art or '—'}",
        EST["assin"]))
    A(Spacer(1, 8))
    A(Paragraph(
        f"Documento emitido em {emissao} por {NOME_PRODUTO} v{VERSAO_MOTOR}, com base na "
        f"{NORMA_APLICADA}. A impressão digital SHA-256 dos dados de entrada é "
        f"<font face='Courier'>{hash_dados}</font>. O arquivo de projeto correspondente "
        "reproduz integralmente esta análise.", EST["nota"]))

    doc.build(el)
    pdf = buf.getvalue()
    buf.close()
    return pdf
