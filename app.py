"""SPDA Risk Pro — interface web (Streamlit).

Regra de ouro desta camada: a interface NÃO calcula nada. Ela coleta, valida e
apresenta. Todo número vem do pacote `spda`, que não conhece Streamlit.
"""

from __future__ import annotations

import time
from datetime import date

import pandas as pd
import streamlit as st

from spda import analise, ng, projeto_io, tabelas as T, validacao
from spda.auth import ControleTentativas, gerar_hash, sessao_expirada, verificar
from spda.laudo import gerar_laudo
from spda.notificacao import (
    DESTINATARIO_PADRAO,
    ConfigEmail,
    Solicitacao,
    email_valido,
    enviar,
    usuario_valido,
)
from spda.modelo import (
    Estrutura,
    EstruturaAdjacente,
    Identificacao,
    LinhaEletrica,
    Projeto,
    SistemaInterno,
    Trecho,
    ZonaEstudo,
)
from spda.versao import NOME_PRODUTO, NORMA_APLICADA, VERSAO_APP, VERSAO_MOTOR

st.set_page_config(page_title=f"{NOME_PRODUTO} — NBR 5419-2:2026",
                   layout="wide", page_icon="⚡")


# =============================================================================
# Autenticação
# =============================================================================
def _controle() -> ControleTentativas:
    if "_tentativas" not in st.session_state:
        st.session_state._tentativas = ControleTentativas()
    return st.session_state._tentativas


def _usuarios_configurados() -> tuple[dict, str | None]:
    """Devolve (usuários, erro).

    Distinguir "não há segredos" de "os segredos estão quebrados" importa: o
    primeiro caso é o primeiro acesso normal; o segundo é TOML colado errado, e
    aí o usuário precisa de uma mensagem que diga isso, não da tela de cadastro
    de novo. A supressão evita que o Streamlit desenhe uma caixa vermelha com
    caminhos internos do servidor antes de a nossa tela aparecer.
    """
    try:
        st.secrets.set_suppress_print_error_on_exception(True)
    except Exception:
        pass
    try:
        usuarios = st.secrets.get("usuarios", None)
    except FileNotFoundError:
        return {}, None
    except Exception as ex:
        return {}, str(ex)
    if not usuarios:
        return {}, None
    try:
        return {str(k): str(v) for k, v in dict(usuarios).items()}, None
    except Exception as ex:
        return {}, str(ex)


def _config_email() -> ConfigEmail:
    """Configuração SMTP, lida do bloco [email] dos segredos.

    Ausente, o app continua funcionando: a solicitação passa a ser entregue
    pela tela, para o solicitante encaminhar. Nenhum caminho depende do e-mail.
    """
    try:
        st.secrets.set_suppress_print_error_on_exception(True)
    except Exception:
        pass
    try:
        bloco = dict(st.secrets.get("email", {}) or {})
    except Exception:
        bloco = {}
    try:
        porta = int(bloco.get("porta", 465))
    except (TypeError, ValueError):
        porta = 465
    return ConfigEmail(
        remetente=str(bloco.get("remetente", "")),
        senha_app=str(bloco.get("senha_app", "")),
        destinatario=str(bloco.get("destinatario", DESTINATARIO_PADRAO)),
        servidor=str(bloco.get("servidor", "smtp.gmail.com")),
        porta=porta,
    )


LIMITE_SOLICITACOES_POR_SESSAO = 3


def _bloco_credencial(usuario: str, senha: str) -> str:
    return f'{usuario} = "{gerar_hash(senha)}"'


def _form_solicitacao() -> None:
    """Formulário público de solicitação de acesso.

    O que sai daqui é a linha pronta para o bloco [usuarios] dos segredos —
    nunca a senha em claro. Ver `spda/notificacao.py` para o porquê.
    """
    cfg = _config_email()

    st.markdown(
        "Preencha os dados abaixo para solicitar uma conta. A liberação é "
        "manual: você recebe um retorno assim que o acesso for habilitado."
    )

    with st.form("solicitar_acesso", clear_on_submit=False):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome completo *", key="sol_nome").strip()
        email_contato = c2.text_input("E-mail *", key="sol_email").strip()
        c3, c4 = st.columns(2)
        telefone = c3.text_input("Telefone ou WhatsApp", key="sol_tel").strip()
        organizacao = c4.text_input("Empresa", key="sol_org").strip()
        crea = st.text_input("Registro no CREA", key="sol_crea").strip()

        st.markdown("**Escolha suas credenciais de acesso**")
        c5, c6, c7 = st.columns(3)
        usuario = c5.text_input("Usuário desejado *", key="sol_usuario").strip()
        s1 = c6.text_input("Senha *", type="password", key="sol_senha1")
        s2 = c7.text_input("Repita a senha *", type="password", key="sol_senha2")
        st.caption(
            "Usuário: 3 a 32 caracteres, sem espaços nem acentos. "
            "Senha: pelo menos 10 caracteres."
        )
        observacao = st.text_area(
            "Alguma observação? (opcional)", height=80, key="sol_obs",
            placeholder="Ex.: tipo de obra, volume de laudos por mês, prazo.",
        )
        enviar_form = st.form_submit_button(
            "Enviar solicitação", use_container_width=True, type="primary"
        )

    if not enviar_form:
        return

    feitas = st.session_state.get("_solicitacoes_enviadas", 0)
    if feitas >= LIMITE_SOLICITACOES_POR_SESSAO:
        st.error(
            "Limite de solicitações desta sessão atingido. Recarregue a página "
            f"ou escreva diretamente para {cfg.destinatario}."
        )
        return

    problemas = []
    if len(nome) < 3:
        problemas.append("Informe o nome completo.")
    if not email_valido(email_contato):
        problemas.append("Informe um e-mail válido.")
    if not usuario_valido(usuario):
        problemas.append(
            "Usuário inválido: use de 3 a 32 caracteres, começando por letra ou "
            "número, sem espaços nem acentos."
        )
    if len(s1) < 10:
        problemas.append("A senha precisa ter pelo menos 10 caracteres.")
    elif s1 != s2:
        problemas.append("As duas senhas não são iguais.")
    if problemas:
        for m in problemas:
            st.error(m)
        return

    credencial = _bloco_credencial(usuario, s1)
    solicitacao = Solicitacao(
        nome=nome, email=email_contato, usuario=usuario, credencial=credencial,
        telefone=telefone, organizacao=organizacao, crea=crea,
        observacao=observacao.strip(),
    )
    ok, detalhe = enviar(cfg, solicitacao)
    st.session_state["_solicitacoes_enviadas"] = feitas + 1

    # Registro nos logs do servidor: é o caminho de recuperação do
    # administrador quando o e-mail falha (Manage app → logs).
    print(
        f"[SOLICITACAO DE ACESSO] {solicitacao.momento} | {nome} <{email_contato}> "
        f"| usuario={usuario} | email_enviado={ok} | {credencial}",
        flush=True,
    )

    if ok:
        st.success(
            f"Solicitação enviada. Assim que o acesso for liberado, você recebe "
            f"um aviso em **{email_contato}**.",
            icon="✅",
        )
    else:
        if cfg.configurado:
            explicacao = "O envio automático falhou desta vez."
        else:
            explicacao = "Este app ainda não envia e-mail automaticamente."
        st.warning(
            f"{explicacao} Sua solicitação está pronta abaixo: copie o bloco e "
            f"envie para **{cfg.destinatario}** que o acesso será liberado.",
            icon="✉️",
        )

    with st.expander(
        "Código técnico da sua solicitação (guarde ou encaminhe se pedirem)",
        expanded=not ok,
    ):
        st.code(f"[usuarios]\n{credencial}", language="toml")
        st.caption(
            "Este código não é a sua senha e não abre o app sozinho: é a "
            "verificação criptográfica que o administrador cadastra no servidor. "
            "A senha que você escolheu não sai do seu navegador em lugar nenhum "
            "— nem por e-mail, nem aqui. Por isso ela também não pode ser "
            "recuperada: se esquecer, faça uma nova solicitação."
        )


def _pagina_entrada(hashes: dict, erro_segredos: str | None) -> None:
    esq, meio, dir_ = st.columns([1, 2.2, 1])
    with meio:
        st.markdown(f"# ⚡ {NOME_PRODUTO}")
        st.caption(
            f"Análise de risco contra descargas atmosféricas · {NORMA_APLICADA}"
        )

        if erro_segredos:
            st.error(
                "**Os segredos deste app existem, mas não puderam ser lidos.** "
                "Costuma ser erro de digitação no bloco colado em "
                "Settings → Secrets: confira se há uma linha `[usuarios]` e se "
                "cada credencial está entre aspas duplas.\n\n"
                f"Detalhe técnico: `{erro_segredos}`",
                icon="⚠️",
            )

        aba_entrar, aba_acesso = st.tabs(["Entrar", "Solicitar acesso"])

        with aba_entrar:
            if not hashes:
                st.info(
                    "Este app ainda não tem nenhum usuário cadastrado. Use a aba "
                    "**Solicitar acesso** para gerar a primeira credencial.",
                    icon="🔑",
                )
            with st.form("login"):
                usuario = st.text_input("Usuário", key="login_usuario").strip()
                senha = st.text_input("Senha", type="password", key="login_senha")
                entrar = st.form_submit_button("Entrar", use_container_width=True)
            if entrar:
                ctrl = _controle()
                ate = ctrl.bloqueado_ate(usuario)
                if ate:
                    st.error(
                        "Muitas tentativas. Tente novamente em "
                        f"{int(ate - time.time()) // 60 + 1} minuto(s)."
                    )
                elif usuario in hashes and verificar(senha, hashes[usuario]):
                    ctrl.limpar(usuario)
                    st.session_state["usuario"] = usuario
                    st.session_state["inicio_sessao"] = time.time()
                    st.rerun()
                else:
                    ctrl.registrar_falha(usuario)
                    st.error("Usuário ou senha inválidos.")

        with aba_acesso:
            _form_solicitacao()

    st.stop()


def exigir_login() -> str:
    if st.session_state.get("usuario") and not sessao_expirada(
        st.session_state.get("inicio_sessao", 0)
    ):
        return st.session_state["usuario"]

    st.session_state.pop("usuario", None)
    hashes, erro_segredos = _usuarios_configurados()
    _pagina_entrada(hashes, erro_segredos)
    raise RuntimeError("inalcançável: _pagina_entrada termina em st.stop()")


USUARIO = exigir_login()


# =============================================================================
# Estado
# =============================================================================
def projeto() -> Projeto:
    if "projeto" not in st.session_state:
        # Semente de localidade: a primeira UF da lista seria o Acre, o que só
        # gera confusão. Petrolina/PE é o padrão de trabalho; muda em um clique.
        try:
            semente = ng.buscar("Petrolina", "PE")
            municipio, uf, n_g = semente.nome, semente.uf, semente.ng
        except Exception:
            municipio, uf, n_g = "", "", 0.0
        st.session_state.projeto = Projeto(
            identificacao=Identificacao(data_emissao=date.today().strftime("%d/%m/%Y")),
            municipio=municipio, uf=uf, n_g=n_g,
        )
    return st.session_state.projeto


P = projeto()


def opcoes(tabela: dict) -> list[str]:
    return list(tabela.keys())


def rotulo_de(tabela: dict):
    return lambda k: f"{T.valor(tabela, k):g} — {T.rotulo(tabela, k)}"


def indice(tabela: dict, chave: str) -> int:
    ks = opcoes(tabela)
    return ks.index(chave) if chave in ks else 0


# =============================================================================
# Barra lateral — projeto, cenários, sessão
# =============================================================================
with st.sidebar:
    st.markdown(f"### ⚡ {NOME_PRODUTO}")
    st.caption(f"App v{VERSAO_APP} · motor v{VERSAO_MOTOR}")
    st.caption(NORMA_APLICADA)
    st.divider()

    st.markdown("**Arquivo de projeto**")
    st.download_button(
        "⬇️ Salvar projeto (.json)",
        data=projeto_io.para_json(P).encode("utf-8"),
        file_name=f"projeto_spda_{(P.identificacao.obra or 'sem_nome')[:40].replace(' ', '_')}.json",
        mime="application/json",
        use_container_width=True,
    )
    enviado = st.file_uploader("Abrir projeto", type=["json"], label_visibility="collapsed")
    if enviado is not None and st.button("Carregar arquivo", use_container_width=True):
        try:
            st.session_state.projeto = projeto_io.de_json(enviado.getvalue())
            st.session_state.pop("cenario_base", None)
            st.success("Projeto carregado.")
            st.rerun()
        except Exception as e:
            st.error(f"Arquivo inválido: {e}")

    st.divider()
    st.markdown("**Comparação de cenários** (D.2)")
    if st.button("📌 Fixar cenário atual como referência", use_container_width=True):
        st.session_state.cenario_base = projeto_io.clonar(P)
        st.success("Cenário de referência fixado.")
    if "cenario_base" in st.session_state:
        st.caption("Referência fixada — a aba de resultados mostra o comparativo.")
        if st.button("Limpar referência", use_container_width=True):
            st.session_state.pop("cenario_base")
            st.rerun()

    st.divider()
    st.caption(f"Sessão: **{USUARIO}**")
    if st.button("🚪 Sair", use_container_width=True):
        for k in ("usuario", "inicio_sessao"):
            st.session_state.pop(k, None)
        st.rerun()


st.title("Análise de risco contra descargas atmosféricas")

abas = st.tabs([
    "1 · Identificação",
    "2 · Localidade (Anexo F)",
    "3 · Estrutura",
    "4 · Linhas elétricas",
    "5 · Zonas de estudo",
    "6 · Resultados e laudo",
])


# =============================================================================
# 1 — Identificação
# =============================================================================
with abas[0]:
    st.subheader("Identificação do trabalho")
    st.caption(
        "Estes dados vão para a capa do laudo. Sem responsável técnico e CREA, "
        "o documento sai sem identificação profissional."
    )
    i = P.identificacao
    c1, c2 = st.columns(2)
    i.obra = c1.text_input("Obra / edificação", i.obra)
    i.proprietario = c2.text_input("Proprietário", i.proprietario)
    i.endereco = st.text_input("Endereço", i.endereco)
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    i.responsavel_tecnico = c1.text_input("Responsável técnico", i.responsavel_tecnico)
    i.crea = c2.text_input("CREA", i.crea)
    i.art = c3.text_input("ART", i.art)
    i.data_emissao = c4.text_input("Data de emissão", i.data_emissao)
    P.observacoes = st.text_area(
        "Observações do responsável técnico (vão para o laudo)", P.observacoes, height=110
    )


# =============================================================================
# 2 — Localidade
# =============================================================================
with abas[1]:
    st.subheader("Densidade de descargas atmosféricas N_G")
    st.info(
        "**A.1.3 e F.1.1** — os valores de N_G devem ser exclusivamente os do Anexo F. "
        "Dados de outras fontes não podem ser utilizados. A base embarcada tem "
        f"{len(ng.carregar()):,} municípios.".replace(",", "."),
        icon="📕",
    )
    c1, c2, c3 = st.columns([1, 2, 1])
    uf_atual = P.uf if P.uf in ng.ufs() else ng.ufs()[0]
    uf = c1.selectbox("UF", ng.ufs(), index=ng.ufs().index(uf_atual))
    lista = ng.municipios_da_uf(uf)
    nomes = [m.nome for m in lista]
    idx = nomes.index(P.municipio) if P.municipio in nomes else 0
    nome = c2.selectbox("Município", nomes, index=idx)
    escolhido = ng.buscar(nome, uf)
    c3.metric("N_G (Tabela F.1)", f"{escolhido.ng:g}", help="raios/km²/ano")

    P.municipio, P.uf = escolhido.nome, escolhido.uf

    P.n_g_sobrescrito = st.checkbox(
        "Sobrescrever N_G (somente por imposição de autoridade com jurisdição)",
        P.n_g_sobrescrito,
    )
    if P.n_g_sobrescrito:
        cc1, cc2 = st.columns([1, 3])
        P.n_g = cc1.number_input("N_G adotado", min_value=0.0, value=float(P.n_g or escolhido.ng), step=0.5)
        P.n_g_justificativa = cc2.text_input(
            "Justificativa (obrigatória, impressa no laudo)", P.n_g_justificativa
        )
    else:
        P.n_g = escolhido.ng
        P.n_g_justificativa = ""
    st.caption(f"N_G adotado na análise: **{P.n_g:g} raios/km²/ano**")


# =============================================================================
# 3 — Estrutura
# =============================================================================
with abas[2]:
    st.subheader("Geometria e medidas de proteção da estrutura")
    e = P.estrutura
    modo_grafico = st.checkbox(
        "Forma complexa — A_D determinada por método gráfico (A.2.1.3.1)",
        e.a_d_informada_m2 is not None,
    )
    if modo_grafico:
        c1, c2 = st.columns([1, 3])
        e.a_d_informada_m2 = c1.number_input(
            "A_D (m²)", min_value=0.0, value=float(e.a_d_informada_m2 or 0.0), step=10.0
        )
        e.a_d_justificativa = c2.text_input("Descrição do método adotado", e.a_d_justificativa)
        st.caption("A_M continua sendo calculada pela eq. (A.6) a partir de L e W.")
    else:
        e.a_d_informada_m2 = None

    c1, c2, c3, c4 = st.columns(4)
    e.comprimento_m = c1.number_input("Comprimento L (m)", min_value=0.0, value=e.comprimento_m, step=0.5)
    e.largura_m = c2.number_input("Largura W (m)", min_value=0.0, value=e.largura_m, step=0.5)
    e.altura_m = c3.number_input("Altura H (m)", min_value=0.0, value=e.altura_m, step=0.5)
    e.altura_saliencia_m = c4.number_input(
        "Altura da saliência H_P (m)", min_value=0.0, value=e.altura_saliencia_m, step=0.5,
        help="A.2.1.3.2 — antena, chaminé, casa de máquinas. Adota-se o maior entre A_D(H) e π(3·H_P)².",
    )
    e.c_d_chave = st.selectbox(
        "Fator de localização C_D (Tabela A.1)", opcoes(T.C_D),
        index=indice(T.C_D, e.c_d_chave), format_func=rotulo_de(T.C_D),
    )

    c1, c2 = st.columns(2)
    c1.metric("A_D", f"{e.a_d():,.1f} m²".replace(",", "."))
    c2.metric("A_M", f"{e.a_m():,.1f} m²".replace(",", "."))

    st.divider()
    st.markdown("##### Medidas de proteção de âmbito estrutural")
    c1, c2 = st.columns(2)
    P.p_b_chave = c1.selectbox(
        "SPDA externo — P_B (Tabela B.2)", opcoes(T.P_B),
        index=indice(T.P_B, P.p_b_chave), format_func=rotulo_de(T.P_B),
    )
    P.p_eb_chave = c2.selectbox(
        "DPS classe I na entrada — P_EB (Tabela B.7)", opcoes(T.P_EB),
        index=indice(T.P_EB, P.p_eb_chave), format_func=rotulo_de(T.P_EB),
    )

    st.divider()
    st.markdown("##### Pessoas e criticidade")
    c1, c2 = st.columns(2)
    P.pessoas_total = c1.number_input(
        "Total de pessoas na estrutura n_t", min_value=1.0, value=max(P.pessoas_total, 1.0), step=1.0,
        help="C.3.1 b — a soma das pessoas por zona não pode exceder este valor.",
    )
    P.sistema_critico = c2.checkbox(
        "Sistema crítico (7.3.3)", P.sistema_critico,
        help="Sistema cuja falha pode afetar uma comunidade. Fixa F_T = 0,1/ano — "
             "valor que a norma diz expressamente não poder ser alterado (7.3.4).",
    )
    st.caption(
        f"Frequência tolerável adotada: **F_T = {P.f_t:g} /ano** "
        f"({'sistema crítico — 7.3.4' if P.sistema_critico else 'sistema não crítico, valor representativo'})"
    )

    st.divider()
    st.markdown("##### Perda ambiental (C.3.2 / D.3.2)")
    P.perda_ambiental = st.checkbox(
        "O dano à estrutura pode envolver as vizinhanças ou o meio ambiente "
        "(emissões químicas ou radioativas)", P.perda_ambiental,
    )
    if P.perda_ambiental:
        c1, c2, c3 = st.columns(3)
        P.l_fe = c1.number_input("L_FE", min_value=0.0, value=P.l_fe, step=0.1,
                                 help="Nota 1 de C.3.2: se desconhecido, assumir 1.")
        P.horas_presenca_externa_ano = c2.number_input(
            "t_e (h/ano)", min_value=0.0, max_value=8760.0,
            value=P.horas_presenca_externa_ano, step=100.0)
        P.valores_externos = c3.number_input(
            "c_e — valores externos em perigo (R$)", min_value=0.0,
            value=P.valores_externos, step=1000.0)


# =============================================================================
# 4 — Linhas elétricas
# =============================================================================
with abas[3]:
    st.subheader("Linhas elétricas conectadas à estrutura")
    st.caption(
        "6.8 — cada linha pode ser dividida em trechos S_L. Todo crédito de "
        "blindagem depende de atributos declarados: nada é inferido."
    )

    if st.button("➕ Nova linha"):
        P.linhas.append(LinhaEletrica(id_linha=f"Linha {len(P.linhas) + 1}"))
        st.rerun()

    for li, ln in enumerate(P.linhas):
        with st.expander(f"🔌 {ln.id_linha} — {ln.tipo}", expanded=len(P.linhas) <= 2):
            c1, c2, c3 = st.columns([2, 1, 1])
            ln.id_linha = c1.text_input("Identificação", ln.id_linha, key=f"lid{li}")
            ln.tipo = c2.selectbox("Tipo", ["energia", "sinal"],
                                   index=0 if ln.tipo == "energia" else 1, key=f"lt{li}")
            if c3.button("🗑️ Remover", key=f"ldel{li}"):
                P.linhas.pop(li)
                st.rerun()

            st.markdown("**Trechos (6.8)**")
            for ti, tr in enumerate(ln.trechos):
                t1, t2, t3, t4, t5, t6 = st.columns([1.4, 1, 1.4, 1.4, 1.4, 0.7])
                tr.id_trecho = t1.text_input("Trecho", tr.id_trecho, key=f"tid{li}{ti}")
                tr.comprimento_m = t2.number_input(
                    "L_L (m)", min_value=0.0, value=tr.comprimento_m, step=50.0, key=f"tl{li}{ti}",
                    help="A.4.1 — se desconhecido, assumir 1 000 m.")
                tr.c_i_chave = t3.selectbox("C_I", opcoes(T.C_I), index=indice(T.C_I, tr.c_i_chave),
                                            format_func=rotulo_de(T.C_I), key=f"tci{li}{ti}")
                tr.c_e_chave = t4.selectbox("C_E", opcoes(T.C_E), index=indice(T.C_E, tr.c_e_chave),
                                            format_func=rotulo_de(T.C_E), key=f"tce{li}{ti}")
                tr.c_t_chave = t5.selectbox("C_T", opcoes(T.C_T), index=indice(T.C_T, tr.c_t_chave),
                                            format_func=rotulo_de(T.C_T), key=f"tct{li}{ti}")
                if t6.button("🗑️", key=f"tdel{li}{ti}") and len(ln.trechos) > 1:
                    ln.trechos.pop(ti)
                    st.rerun()
                if tr.enterrado:
                    tr.resistividade_solo_ohm_m = st.number_input(
                        f"ρ do solo no trecho {tr.id_trecho} (Ω·m)", min_value=1.0,
                        value=tr.resistividade_solo_ohm_m, step=50.0, key=f"trho{li}{ti}",
                        help="Nota 1 da Tabela A.2 — acima de 400 Ω·m, A_L = 0,6·√ρ·L_L.")
            if st.button("➕ Trecho", key=f"tadd{li}"):
                ln.trechos.append(Trecho(id_trecho=f"Trecho {len(ln.trechos) + 1}"))
                st.rerun()

            st.markdown("**Blindagem e equipotencialização (Tabelas B.4 e B.8)**")
            b1, b2, b3 = st.columns(3)
            ln.blindada = b1.checkbox("Linha blindada", ln.blindada, key=f"lb{li}")
            if ln.blindada:
                ln.blindagem_no_mesmo_bep = b2.checkbox(
                    "Blindagem interligada ao mesmo BEP do equipamento",
                    ln.blindagem_no_mesmo_bep, key=f"lbep{li}",
                    help="Tabela B.8 — sem isto a blindagem não é creditada: P_LD = 1.")
                ln.resistencia_blindagem_ohm_km = b3.number_input(
                    "R_S da blindagem (Ω/km)", min_value=0.0,
                    value=ln.resistencia_blindagem_ohm_km, step=0.5, key=f"lrs{li}")
            else:
                ln.blindagem_no_mesmo_bep = False

            d1, d2, d3 = st.columns(3)
            ln.cabo_protecao_ou_conduto_metalico = d1.checkbox(
                "Eletroduto/tubo metálico ou cabo de proteção", ln.cabo_protecao_ou_conduto_metalico,
                key=f"lcond{li}")
            if ln.tipo == "energia":
                ln.neutro_multiaterrado = d2.checkbox(
                    "Neutro multiaterrado", ln.neutro_multiaterrado, key=f"lnm{li}",
                    help="Tabela B.4 — característica declarada da instalação. "
                         "Não é consequência de a linha ser BT.")
            else:
                ln.neutro_multiaterrado = False
            ln.sem_linha_externa = d3.checkbox(
                "Sistema independente / linha não metálica (fibra)", ln.sem_linha_externa,
                key=f"lsl{li}")

            ln.interface_isolante = st.checkbox(
                "Possui interface isolante conforme NBR 5419-4", ln.interface_isolante, key=f"lii{li}")
            if ln.interface_isolante:
                ln.interface_isolante_protegida_por_dps = st.checkbox(
                    "Interface isolante protegida por DPS (ou U_W ensaiado superior ao do ponto)",
                    ln.interface_isolante_protegida_por_dps, key=f"liid{li}",
                    help="Nota a da Tabela B.4 — sem isto, C_LD = 1.")

            tem_adj = st.checkbox("Estrutura adjacente na extremidade da linha (N_DJ)",
                                  ln.estrutura_adjacente is not None, key=f"ladj{li}")
            if tem_adj:
                if ln.estrutura_adjacente is None:
                    ln.estrutura_adjacente = EstruturaAdjacente()
                a = ln.estrutura_adjacente
                a1, a2, a3, a4 = st.columns(4)
                a.comprimento_m = a1.number_input("L_J (m)", min_value=0.0, value=a.comprimento_m,
                                                  step=1.0, key=f"aj1{li}")
                a.largura_m = a2.number_input("W_J (m)", min_value=0.0, value=a.largura_m,
                                              step=1.0, key=f"aj2{li}")
                a.altura_m = a3.number_input("H_J (m)", min_value=0.0, value=a.altura_m,
                                             step=0.5, key=f"aj3{li}")
                a.c_dj_chave = a4.selectbox("C_DJ", opcoes(T.C_D), index=indice(T.C_D, a.c_dj_chave),
                                            format_func=rotulo_de(T.C_D), key=f"aj4{li}")
            else:
                ln.estrutura_adjacente = None

            c_ld, c_li = ln.c_ld_c_li()
            st.caption(
                f"→ Tabela B.4: **C_LD = {c_ld:g}**, **C_LI = {c_li:g}** · "
                f"Tabela B.8: faixa **{ln.faixa_p_ld.replace('_', ' ')}**"
            )

    if P.linhas:
        st.dataframe(pd.DataFrame([{
            "Linha": l.id_linha, "Tipo": l.tipo, "Trechos": len(l.trechos),
            "Comprimento total (m)": sum(t.comprimento_m for t in l.trechos),
            "C_LD": l.c_ld_c_li()[0], "C_LI": l.c_ld_c_li()[1],
            "Faixa B.8": l.faixa_p_ld.replace("_", " "),
            "Adjacente": "sim" if l.estrutura_adjacente else "não",
        } for l in P.linhas]), use_container_width=True, hide_index=True)


# =============================================================================
# 5 — Zonas de estudo
# =============================================================================
with abas[4]:
    st.subheader("Zonas de estudo Z_S")
    st.caption(
        "6.7 — cada zona tem características homogêneas e SUAS PRÓPRIAS medidas "
        "de proteção. Nenhum parâmetro de uma zona é aplicado às demais."
    )
    if st.button("➕ Nova zona"):
        P.zonas.append(ZonaEstudo(
            id_zona=f"Zona {len(P.zonas) + 1}",
            sistemas_internos=[SistemaInterno(id_sistema="Sistema 1")],
        ))
        st.rerun()

    ids_linhas = [l.id_linha for l in P.linhas]

    for zi, z in enumerate(P.zonas):
        with st.expander(f"🏢 {z.id_zona} — {z.perdas['rotulo']}", expanded=len(P.zonas) <= 2):
            c1, c2, c3 = st.columns([2, 2, 1])
            z.id_zona = c1.text_input("Identificação", z.id_zona, key=f"zid{zi}")
            z.ocupacao = c2.selectbox(
                "Tipo de ocupação", list(T.OCUPACOES),
                index=list(T.OCUPACOES).index(z.ocupacao) if z.ocupacao in T.OCUPACOES else 0,
                format_func=lambda k: T.OCUPACOES[k][0], key=f"zoc{zi}",
                help="Define L_F e L_O simultaneamente nas três tabelas: C.2 (L1), "
                     "C.9 (L3) e D.2 (L4).",
            )
            if c3.button("🗑️ Remover", key=f"zdel{zi}"):
                P.zonas.pop(zi)
                st.rerun()

            pd_ = z.perdas
            st.caption(
                f"→ L1 (Tabela C.2): L_F = {pd_['L_F_L1']:g} · L_O = {pd_['L_O_L1']:g}  |  "
                f"L3 (Tabela C.9): L_F = {pd_['L_F_L3']:g}  |  "
                f"L4 (Tabela D.2): L_F = {pd_['L_F_L4']:g} · L_O = {pd_['L_O_L4']:g}"
            )

            st.markdown("**Pessoas e fatores de perda**")
            p1, p2 = st.columns(2)
            z.pessoas_na_zona = p1.number_input("Pessoas na zona n_z", min_value=0.0,
                                                value=z.pessoas_na_zona, step=1.0, key=f"znz{zi}")
            z.horas_presenca_ano = p2.number_input("Tempo de presença t_z (h/ano)", min_value=0.0,
                                                   max_value=8760.0, value=z.horas_presenca_ano,
                                                   step=100.0, key=f"ztz{zi}")
            f1, f2, f3 = st.columns(3)
            z.r_t_chave = f1.selectbox("r_t — piso (Tabela C.3)", opcoes(T.R_T),
                                       index=indice(T.R_T, z.r_t_chave),
                                       format_func=rotulo_de(T.R_T), key=f"zrt{zi}")
            z.r_f_chave = f2.selectbox("r_f — incêndio/explosão (Tabela C.5)", opcoes(T.R_F),
                                       index=indice(T.R_F, z.r_f_chave),
                                       format_func=rotulo_de(T.R_F), key=f"zrf{zi}")
            z.r_s_chave = f3.selectbox("r_s — construção (Tabela C.7)", opcoes(T.R_S_CONSTRUCAO),
                                       index=indice(T.R_S_CONSTRUCAO, z.r_s_chave),
                                       format_func=rotulo_de(T.R_S_CONSTRUCAO), key=f"zrs{zi}")
            g1, g2 = st.columns(2)
            z.r_p_chave = g1.selectbox(
                "r_p — providências contra incêndio (Tabela C.4)", opcoes(T.R_P),
                index=indice(T.R_P, z.r_p_chave), format_func=rotulo_de(T.R_P),
                key=f"zrp{zi}", disabled=z.risco_de_explosao,
            )
            z.h_z_chave = g2.selectbox("h_z — perigo especial (Tabela C.6)", opcoes(T.H_Z),
                                       index=indice(T.H_Z, z.h_z_chave),
                                       format_func=rotulo_de(T.H_Z), key=f"zhz{zi}")
            if z.risco_de_explosao:
                st.warning(
                    "Zona com risco de explosão: **r_p forçado a 1,00** (C.3.4) e as "
                    "componentes R_C, R_M, R_W e R_Z passam a compor R1 obrigatoriamente "
                    "(nota *a* da Tabela 2).", icon="⚠️",
                )

            st.markdown("**Proteção contra tensões de toque e passo**")
            t1, t2 = st.columns(2)
            z.p_ta_chaves = t1.multiselect(
                "P_TA — na estrutura (Tabela B.1)", opcoes(T.P_TA),
                default=z.p_ta_chaves or ["nenhuma"], format_func=rotulo_de(T.P_TA), key=f"zpta{zi}",
                help="B.2.2 — múltiplas medidas: o valor é o produto.",
            ) or ["nenhuma"]
            z.p_tu_chaves = t2.multiselect(
                "P_TU — na linha (Tabela B.6)", opcoes(T.P_TU),
                default=z.p_tu_chaves or ["nenhuma"], format_func=rotulo_de(T.P_TU), key=f"zptu{zi}",
                help="Nota 1 da Tabela B.6 — múltiplas medidas: o valor é o produto.",
            ) or ["nenhuma"]
            st.caption(f"→ P_TA = {z.p_ta:g} · P_TU = {z.p_tu:g}")

            st.markdown("**Blindagem espacial (B.4.12)**")
            s1, s2, s3 = st.columns(3)
            z.blindagem_continua_zpr01 = s1.checkbox("Blindagem contínua ZPR 0/1",
                                                     z.blindagem_continua_zpr01, key=f"zbc1{zi}")
            if not z.blindagem_continua_zpr01:
                z.largura_malha_zpr01_m = s1.number_input("w_m1 (m)", min_value=0.0,
                                                          value=z.largura_malha_zpr01_m,
                                                          step=0.5, key=f"zwm1{zi}")
            z.blindagem_continua_zprxy = s2.checkbox("Blindagem contínua ZPR X/Y",
                                                     z.blindagem_continua_zprxy, key=f"zbc2{zi}")
            if not z.blindagem_continua_zprxy:
                z.largura_malha_zprxy_m = s2.number_input("w_m2 (m)", min_value=0.0,
                                                          value=z.largura_malha_zprxy_m,
                                                          step=0.5, key=f"zwm2{zi}")
            z.rede_equipotencial_em_malha = s3.checkbox(
                "Rede de equipotencialização em malha", z.rede_equipotencial_em_malha,
                key=f"zreq{zi}", help="Nota de B.4.12 — reduz K_S1 e K_S2 à metade.")
            st.caption(f"→ K_S1 = {z.k_s1():g} · K_S2 = {z.k_s2():g}")

            st.markdown("**Sistemas internos** — base das eq. (12) e (13)")
            for si, s in enumerate(z.sistemas_internos):
                q1, q2, q3, q4, q5 = st.columns([1.8, 1, 1.4, 1.4, 0.6])
                s.id_sistema = q1.text_input("Sistema", s.id_sistema, key=f"sid{zi}{si}")
                s.uw_kv = q2.selectbox(
                    "U_W (kV)", list(T.UW_COLUNAS_PLD),
                    index=list(T.UW_COLUNAS_PLD).index(s.uw_kv) if s.uw_kv in T.UW_COLUNAS_PLD else 4,
                    key=f"suw{zi}{si}",
                    help="B.4.15 — usar o MENOR U_W entre os equipamentos do sistema.")
                s.p_spd_chave = q3.selectbox("P_SPD (Tabela B.3)", opcoes(T.P_SPD),
                                             index=indice(T.P_SPD, s.p_spd_chave),
                                             format_func=rotulo_de(T.P_SPD), key=f"sps{zi}{si}")
                s.k_s3_chave = q4.selectbox("K_S3 (Tabela B.5)", opcoes(T.K_S3),
                                            index=indice(T.K_S3, s.k_s3_chave),
                                            format_func=rotulo_de(T.K_S3), key=f"sks{zi}{si}")
                if q5.button("🗑️", key=f"sdel{zi}{si}") and len(z.sistemas_internos) > 1:
                    z.sistemas_internos.pop(si)
                    st.rerun()

                w1, w2, w3, w4 = st.columns(4)
                s.blindado = w1.checkbox("Sistema interno blindado", s.blindado, key=f"sbl{zi}{si}",
                                         help="B.4.4 — se não blindado, C_LD = 1 em P_C.")
                s.interface_optica = w2.checkbox("Interface óptica", s.interface_optica,
                                                 key=f"sio{zi}{si}", help="B.4.11 — P_MS = 0.")
                s.em_zpr0a = w3.checkbox("Equipamento em ZPR0A", s.em_zpr0a, key=f"szp{zi}{si}",
                                         help="7.1.5 — habilita F_B = N_D × P_B.")
                s.atende_normas_de_produto = w4.checkbox(
                    "Atende normas de produto (U_W)", s.atende_normas_de_produto,
                    key=f"snp{zi}{si}", help="B.4.10 — se não atende, P_M = 1.")

                s.sistema_independente = st.checkbox(
                    "Sistema independente (sem conexão a linhas externas)",
                    s.sistema_independente, key=f"sind{zi}{si}")
                if not s.sistema_independente:
                    s.ids_linhas = st.multiselect(
                        "Linhas elétricas a que este sistema se conecta", ids_linhas,
                        default=[i for i in s.ids_linhas if i in ids_linhas], key=f"slin{zi}{si}")
                else:
                    s.ids_linhas = []
                st.markdown("---")

            if st.button("➕ Sistema interno", key=f"sadd{zi}"):
                z.sistemas_internos.append(
                    SistemaInterno(id_sistema=f"Sistema {len(z.sistemas_internos) + 1}"))
                st.rerun()

            st.markdown("**Valores econômicos na zona** (Anexos C.4 e D)")
            v1, v2, v3, v4, v5 = st.columns(5)
            z.valor_animais = v1.number_input("c_a — animais", min_value=0.0,
                                              value=z.valor_animais, step=1000.0, key=f"zca{zi}")
            z.valor_edificacao = v2.number_input("c_b — edificação", min_value=0.0,
                                                 value=z.valor_edificacao, step=1000.0, key=f"zcb{zi}")
            z.valor_conteudo = v3.number_input("c_c — conteúdo", min_value=0.0,
                                               value=z.valor_conteudo, step=1000.0, key=f"zcc{zi}")
            z.valor_sistemas = v4.number_input("c_s — sistemas internos", min_value=0.0,
                                               value=z.valor_sistemas, step=1000.0, key=f"zcs{zi}")
            z.valor_patrimonio_cultural = v5.number_input(
                "c_z — patrimônio cultural", min_value=0.0,
                value=z.valor_patrimonio_cultural, step=1000.0, key=f"zcz{zi}",
                help="C.4 — só preencha se houver patrimônio cultural. É o que torna R3 aplicável.")

    st.divider()
    st.markdown("##### Risco de perda econômica R4 (Anexo D — informativo)")
    c1, c2, c3 = st.columns([1, 1.2, 1.4])
    P.avaliar_r4 = c1.checkbox("Avaliar R4", P.avaliar_r4)
    if P.avaliar_r4:
        P.modo_r4 = c2.radio(
            "Modo de avaliação", ["detalhado", "representativo"],
            index=0 if P.modo_r4 == "detalhado" else 1, horizontal=True,
            help="Nota a da Tabela D.1 — no modo representativo as razões c_x/c_t "
                 "são substituídas por 1 e R4 é comparado com R_T = 1e-3.",
        )
    P.valor_total_estrutura = c3.number_input(
        "c_t — valor total da estrutura (R$)", min_value=0.0,
        value=P.valor_total_estrutura, step=10000.0,
        help="D.4 — valor TOTAL da estrutura, soma de todas as zonas. Também é o "
             "denominador de L_B3 quando há patrimônio cultural.")


# =============================================================================
# 6 — Resultados e laudo
# =============================================================================
def _cor(ok):
    return "✅" if ok else ("⚠️" if ok is None else "❌")


with abas[5]:
    st.subheader("Resultados")
    itens = validacao.validar(P)
    erros = validacao.erros(itens)
    avisos = validacao.avisos(itens)

    if erros:
        st.error(f"**{len(erros)} inconsistência(s) impedem a emissão do laudo:**")
        for i in erros:
            st.markdown(f"- **{i.onde}** — {i.mensagem}"
                        + (f"  \n  <small>*{i.clausula}*</small>" if i.clausula else ""),
                        unsafe_allow_html=True)
    if avisos:
        with st.expander(f"⚠️ {len(avisos)} premissa(s) e ressalva(s) — serão impressas no laudo"):
            for i in avisos:
                st.markdown(f"- **{i.onde}** — {i.mensagem}"
                            + (f"  \n  <small>*{i.clausula}*</small>" if i.clausula else ""),
                            unsafe_allow_html=True)

    if erros:
        st.stop()

    R = analise.analisar(P)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(f"{_cor(R.r1_aprovado)} R1 — vida humana", f"{R.r1:.3e}",
              f"limite {T.R_T_R1:.0e}", delta_color="off")
    m2.metric(f"{_cor(R.r3_aprovado)} R3 — patrimônio cultural",
              f"{R.r3:.3e}" if R.r3_aplicavel else "não aplicável",
              f"limite {T.R_T_R3:.0e}", delta_color="off")
    m3.metric(f"{_cor(R.f_aprovado)} F — frequência de danos", f"{R.f:.4f} /ano",
              f"limite {R.f_t:g} /ano", delta_color="off")
    if R.r4_avaliado:
        if P.modo_r4 == "representativo":
            m4.metric(f"{_cor(R.r4_aprovado)} R4 — econômico", f"{R.r4:.3e}",
                      f"limite {T.R_T_R4:.0e}", delta_color="off")
        else:
            m4.metric("R4 — custo provável de perda",
                      f"R$ {R.custo_anual_perda:,.2f}/ano".replace(",", "@").replace(".", ",").replace("@", "."),
                      f"R4 = {R.r4:.3e}", delta_color="off")
    else:
        m4.metric("R4 — econômico", "não avaliado", "Anexo D, informativo", delta_color="off")

    if R.aprovado_geral:
        st.success(
            "**Os riscos avaliados atendem aos valores toleráveis.** Conforme 5.4.3, os "
            "resultados são suficientes.", icon="✅")
    else:
        st.error(
            "**Ao menos um risco supera o valor tolerável.** Conforme 5.4.4, medidas de "
            "proteção devem ser adotadas até que R ≤ R_T para todos os tipos de risco.",
            icon="❌")

    st.divider()
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown("##### Componentes de R1 (5.6.1)")
        comp = R.componentes_r1()
        total = R.r1 or 1.0
        df = pd.DataFrame([
            {"Componente": k.replace("_", ""), "Valor (1/ano)": v,
             "% de R1": 100 * v / total} for k, v in comp.items()
        ])
        st.dataframe(
            df.style.format({"Valor (1/ano)": "{:.4e}", "% de R1": "{:.1f} %"}),
            use_container_width=True, hide_index=True,
        )
        maiores = R.maiores_contribuintes_r1(3)
        if maiores:
            st.caption("**Parâmetros críticos (5.6.2):** " + " · ".join(
                f"{c.replace('_','')} ({p:.1f} %)" for c, _, p in maiores))
    with c2:
        st.markdown("##### Frequência parcial de danos (Tabela 7)")
        cf = R.componentes_f()
        st.dataframe(
            pd.DataFrame([{"Componente": k.replace("_", ""), "Valor (1/ano)": v}
                          for k, v in cf.items()])
            .style.format({"Valor (1/ano)": "{:.5f}"}),
            use_container_width=True, hide_index=True,
        )

    with st.expander("Eventos perigosos (Anexo A) e probabilidades compostas"):
        linhas_tab = [{"Grandeza": "N_D", "Valor (1/ano)": R.n_d, "Eq.": "A.3"},
                      {"Grandeza": "N_M", "Valor (1/ano)": R.n_m, "Eq.": "A.5"}]
        for lid, ev in R.eventos_linhas.items():
            linhas_tab += [
                {"Grandeza": f"N_L — {lid}", "Valor (1/ano)": ev.n_l, "Eq.": "A.7"},
                {"Grandeza": f"N_I — {lid}", "Valor (1/ano)": ev.n_i, "Eq.": "A.9"},
                {"Grandeza": f"N_DJ — {lid}", "Valor (1/ano)": ev.n_dj, "Eq.": "A.4"},
            ]
        st.dataframe(pd.DataFrame(linhas_tab).style.format({"Valor (1/ano)": "{:.5e}"}),
                     use_container_width=True, hide_index=True)
        st.dataframe(pd.DataFrame([
            {"Zona": z.id_zona, "P_C (eq. 12)": z.p_c, "P_M (eq. 13)": z.p_m,
             "R1 da zona": z.r1, "F da zona": z.f} for z in R.zonas
        ]).style.format({"P_C (eq. 12)": "{:.4g}", "P_M (eq. 13)": "{:.4g}",
                         "R1 da zona": "{:.4e}", "F da zona": "{:.5f}"}),
            use_container_width=True, hide_index=True)
        st.caption(
            "7.3.6 — a frequência de danos deve ser comparada com F_T também por zona "
            f"de estudo. F_T adotado: {R.f_t:g}/ano."
        )

    # --- comparação de cenários (D.2) ---
    if "cenario_base" in st.session_state:
        st.divider()
        st.markdown("##### Comparação de cenários (D.2)")
        base = st.session_state.cenario_base
        try:
            Rb = analise.analisar(base)
            comp = pd.DataFrame([
                {"Grandeza": "R1", "Referência": Rb.r1, "Atual": R.r1,
                 "Redução": (1 - R.r1 / Rb.r1) * 100 if Rb.r1 else 0.0},
                {"Grandeza": "R3", "Referência": Rb.r3, "Atual": R.r3,
                 "Redução": (1 - R.r3 / Rb.r3) * 100 if Rb.r3 else 0.0},
                {"Grandeza": "F", "Referência": Rb.f, "Atual": R.f,
                 "Redução": (1 - R.f / Rb.f) * 100 if Rb.f else 0.0},
                {"Grandeza": "R4", "Referência": Rb.r4, "Atual": R.r4,
                 "Redução": (1 - R.r4 / Rb.r4) * 100 if Rb.r4 else 0.0},
            ])
            st.dataframe(comp.style.format({"Referência": "{:.4e}", "Atual": "{:.4e}",
                                            "Redução": "{:+.1f} %"}),
                         use_container_width=True, hide_index=True)
            if Rb.custo_anual_perda and R.custo_anual_perda is not None:
                economia = Rb.custo_anual_perda - R.custo_anual_perda
                st.caption(
                    f"D.2.4 — redução do custo anual de perda: R$ {economia:,.2f}/ano. "
                    "A proteção se justifica economicamente se este valor superar o custo "
                    "anual das medidas C_PM (eq. D.11).".replace(",", "@").replace(".", ",").replace("@", "."))
        except Exception as ex:
            st.warning(f"Não foi possível comparar com a referência: {ex}")

    # --- laudo ---
    st.divider()
    st.markdown("##### Emissão do laudo")
    hash_dados = projeto_io.impressao_digital(P)
    st.caption(f"Motor v{VERSAO_MOTOR} · {NORMA_APLICADA} · "
               f"impressão digital dos dados: `{hash_dados[:16]}`")
    if st.button("📄 Gerar laudo técnico em PDF", type="primary"):
        try:
            pdf = gerar_laudo(P, R, itens)
            nome = (P.identificacao.obra or "laudo").strip()[:50].replace(" ", "_")
            st.download_button("⬇️ Baixar laudo", data=pdf,
                               file_name=f"Laudo_SPDA_{nome}.pdf", mime="application/pdf")
            st.success("Laudo gerado.")
        except Exception as ex:
            st.error(f"Falha ao gerar o laudo: {ex}")
