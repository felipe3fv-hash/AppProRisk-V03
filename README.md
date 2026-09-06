# SPDA Risk Pro — app v2.1.0 · motor v2.0.0

Análise de risco contra descargas atmosféricas conforme **ABNT NBR 5419-2:2026**
(2ª edição, 10.03.2026).

Reescrita completa a partir da auditoria de conformidade do commit `b6aec3e`.
Os 8 achados bloqueantes, 13 graves e 7 de produto foram corrigidos, e cada um
tem hoje um teste de regressão nomeado que impede seu retorno.

---

> **Para publicar no GitHub e no Streamlit Community Cloud, veja
> [`DEPLOY.md`](DEPLOY.md)** — roteiro passo a passo, com as verificações
> pós-deploy e as limitações do plano gratuito.

## Como rodar

```bash
pip install -r requirements-dev.txt
streamlit run app.py
```

A tela de entrada tem duas abas: **Entrar** e **Solicitar acesso**. A segunda é
pública e sempre disponível — é por ela que um cliente pede conta e que você
gera a sua própria credencial na primeira vez. Ela devolve a linha pronta para
o bloco `[usuarios]` dos segredos, e envia a solicitação por e-mail se o bloco
`[email]` estiver configurado. Quem preferir linha de comando:
`python criar_usuario.py mariz`.

```bash
pytest        # 300 testes, ~4 s
```

---

## Arquitetura

Nenhum módulo de cálculo importa Streamlit. A interface é substituível sem
tocar no motor — e é o motor que responde por um laudo assinado.

```
spda/
  tabelas.py        tabelas normativas como DADOS (Anexos A, B, C, D)
  ng.py             Anexo F — N_G por município (5.572 municípios embarcados)
  modelo.py         Projeto · Estrutura · Zona · Sistema interno · Linha · Trecho
  eventos.py        Anexo A — N_D, N_M, N_L, N_I, N_DJ
  probabilidades.py Anexo B — P_A … P_Z, com as eq. (12) e (13)
  perdas.py         Anexos C e D — L_X separado por tipo de perda
  analise.py        Seções 4.3, 6 e 7 — R1, R3, R4 e F, decompostos
  validacao.py      consistência dos dados de entrada (erros bloqueiam o laudo)
  laudo.py          PDF A4 completo
  projeto_io.py     serialização, clonagem de cenários, hash SHA-256
  auth.py           PBKDF2-HMAC-SHA256, bloqueio por tentativas, expiração
  notificacao.py    solicitação de acesso por e-mail (envia o hash, nunca a senha)
app.py              interface web
tests/              300 testes
dados/              ng_municipios.csv (Tabela F.1)
```

### Princípios que sustentam a corretude

1. **Nenhuma tabela da norma vira cadeia de `if`.** Toda tabela é um literal
   indexado em `tabelas.py`, e `tests/test_tabelas.py` percorre célula a célula.
   Foi a ausência disso que produziu os oito desvios de P_LD da versão anterior.
2. **Nada é inferido.** C_LD, C_LI e a faixa de P_LD dependem exclusivamente de
   atributos *declarados* da linha. Uma característica não declarada cai na
   linha mais desfavorável da tabela.
3. **Toda característica zonal mora na zona.** Não existe leitura de `zonas[0]`.
   O resultado não pode depender da ordem de cadastro.
4. **As regras condicionais são derivadas, não escolhidas.** Risco de explosão
   força `r_p = 1` (C.3.4) e a inclusão de R_C/R_M/R_W/R_Z em R1 (nota *a* da
   Tabela 2). Não há checkbox que possa ser esquecido.
5. **Erro de validação bloqueia a emissão.** Aviso não bloqueia, mas é impresso
   no laudo como premissa assumida.

---

## O que mudou em relação à v1

### Bloqueantes

| | Correção |
|---|---|
| **B-01** | N_G vem de um seletor UF → município alimentado pela Tabela F.1 (A.1.3 / F.1.1). Sobrescrita manual exige justificativa, que é carimbada no laudo. |
| **B-02** | L_F e L_O passam a ter três conjuntos distintos — Tabela C.2 (L1), Tabela C.9 (L3) e Tabela D.2 (L4) — preenchidos por uma única escolha de ocupação. A v1 usava os valores de D.2 no cálculo de R1, erro de 2× a 25×. |
| **B-03** | P_TA, P_TU, K_S1 e K_S2 são da zona; U_W, K_S3 e P_SPD são do sistema interno. `Probabilidades` é resolvida por zona dentro do laço da análise. |
| **B-04** | P_LD é uma matriz literal da Tabela B.8 com as 7 colunas de U_W. U_W intermediário arredonda para a coluna inferior (conservador). |
| **B-05** | A interface web expõe enterramento, ρ, mesmo BEP, eletroduto metálico e interface isolante. A blindagem só é creditada quando interligada ao mesmo BEP. |
| **B-06** | Neutro multiaterrado virou campo declarado. Linha BT sem declaração cai em C_LI = 1, como manda a Tabela B.4. |
| **B-07** | F_T = 0,1/ano para sistema crítico (7.3.4), sem opção de edição; 1,0/ano apenas para não crítico, rotulado como representativo. |
| **B-08** | R_C, R_M, R_W e R_Z entram em R1 automaticamente sob risco de explosão ou ocupação hospitalar (nota *a* da Tabela 2). |

### Graves

h_z com os cinco níveis da Tabela C.6, incluindo 10 · r_s (Tabela C.7) exposto ·
c_t é dado único da estrutura, não média por zona · R4 = "não avaliado" em vez
de zero silencioso · eq. (12) e (13) compostas sobre sistemas internos ·
K_S4 do U_W do equipamento interno · F_B incluído com a condição de 7.1.5 ·
P_B, P_TA, P_SPD, P_EB, r_f e r_p completos, com o produto de B.2.2 ·
perda ambiental L_E acessível · R3 "não aplicável" quando não há patrimônio ·
R4 com R_T = 1e-3 e a regra da nota *a* da Tabela D.1 · validação de
consistência em todas as entradas · interface única.

### Produto

Autenticação PBKDF2 com bloqueio, expiração e tela de primeiro acesso ·
300 testes automatizados ·
laudo A4 com ART/CREA, memorial completo, decomposição por componente e
participação percentual, N_D/N_M/N_L/N_I/N_DJ/A_D e assinatura · versão do
motor e hash SHA-256 dos dados de entrada no rodapé de cada página ·
projeto salvável em JSON e comparação de cenários (D.2) · dependências fixadas.

---

## Fluxo de acesso

A aba **Solicitar acesso** coleta nome, e-mail, contato e as credenciais
desejadas, calcula o hash PBKDF2 e envia para `proriskapp@gmail.com` a linha
pronta para colar em `[usuarios]`. Você cadastra em Settings → Secrets e o
acesso passa a valer.

O e-mail **não leva a senha do cliente** — leva o hash. Consequência, e é o
comportamento correto: ninguém, nem você, recupera a senha de um cliente; quem
esquece faz nova solicitação. Sem o bloco `[email]` configurado, o app mostra a
mesma linha na tela para o solicitante encaminhar, e registra tudo nos logs
(Manage app). Nenhum caminho depende do e-mail funcionar.

Isso resolve o cadastro de uns poucos clientes. Para vender plano mensal a
dezenas, o passo seguinte é um cadastro de usuários em banco, com confirmação
de e-mail, recuperação de senha e controle de assinatura — editar segredos à
mão não escala e não tem trilha de auditoria.

---

## Rastreabilidade do laudo

Cada página traz `SPDA Risk Pro v2.0.0 · ABNT NBR 5419-2:2026 · impressão
digital dos dados: <16 dígitos>`. O hash é SHA-256 do projeto normalizado —
independe de formatação, muda com qualquer alteração de valor. Guardando o
`.json` do projeto junto do PDF, qualquer terceiro reproduz a análise e confere
o hash.

**Regra de versionamento:** qualquer alteração em `tabelas.py`,
`probabilidades.py`, `perdas.py`, `eventos.py` ou `analise.py` obriga incremento
de MINOR em `spda/versao.py`. Laudos emitidos com versões diferentes do motor
não são comparáveis sem análise.

---

## Limitações declaradas

Coisas que o motor deliberadamente **não** faz, e que o responsável técnico
precisa saber:

- **Sobreposição de áreas de exposição** entre linhas com o mesmo roteamento
  (nota de 6.4.5) não é detectada automaticamente. Cabe ao projetista aplicar
  6.4.5/6.5.5 e cadastrar apenas a linha de piores características.
- **A_D de forma complexa** exige o método gráfico de A.2.1.3.1. O motor aceita
  o valor determinado pelo projetista e exige a descrição do método, que vai
  para o laudo — mas não desenha nada.
- **P_SPD/P_EB "melhor que NP I"** adotam 0,005, o extremo conservador da faixa
  0,005–0,001 da norma. Valores menores exigem justificativa técnica.
- **R4 é informativo** (D.1.1) e não valida a necessidade de proteção.
- Antes da comercialização, recomenda-se **validação cruzada documentada**
  contra ao menos um software de referência já consolidado no mercado.
