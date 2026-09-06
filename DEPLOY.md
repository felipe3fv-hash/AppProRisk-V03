# Publicar no GitHub e no Streamlit Community Cloud

Roteiro para substituir o conteúdo de `felipe3fv-hash/App` pela v2.0.0 e
publicar o app com acesso restrito a convidados.

Tempo: cerca de 20 minutos. Este roteiro usa terminal. Se você preferir fazer
tudo pelo navegador, sem instalar nada, siga o guia visual que acompanha a
entrega. Para este aqui você precisa de **git** e, opcionalmente, **Python 3.10+**
instalados na sua máquina.

---

## Etapa 0 — Nada a fazer aqui

A senha do primeiro usuário é criada **dentro do próprio app**, depois de
publicado: enquanto não houver nenhum usuário configurado, o app mostra a tela
de primeiro acesso, você escolhe usuário e senha ali, e ele devolve o bloco
pronto para colar nos segredos (Etapa 4).

Se preferir gerar antes, na sua máquina, o utilitário continua existindo:

```bash
pip install -r requirements-dev.txt
python criar_usuario.py mariz
```

---

## Etapa 1 — Tornar o repositório privado

No GitHub, abra `https://github.com/felipe3fv-hash/App` →
**Settings** → role até **Danger Zone** → **Change repository visibility** →
**Make private** → confirme digitando o nome do repositório.

Faça isso **antes** do push. O código passa a valer dinheiro a partir da v2.

---

## Etapa 2 — Substituir o conteúdo do repositório

O ponto crítico: os arquivos da v2 vão para a **raiz** do repositório, e os
nove arquivos da v1 precisam sumir. `spda/ng.py` procura a tabela do Anexo F em
`../dados/ng_municipios.csv`, então a estrutura tem que ficar exatamente assim:

```
App/
├── app.py
├── spda/
├── dados/ng_municipios.csv
├── tests/
├── requirements.txt
└── ...
```

```bash
# 1. clone o repositório atual (mantém o histórico)
git clone https://github.com/felipe3fv-hash/App.git
cd App

# 2. remova TODO o conteúdo antigo, preservando a pasta .git
git rm -r --cached . -q
find . -mindepth 1 -not -path './.git' -not -path './.git/*' -delete

# 3. copie o conteúdo da v2 para cá
#    (ajuste o caminho de onde você descompactou o zip)
cp -R ~/Downloads/spda_app/. .

# 4. confira: app.py tem que estar na raiz e o CSV precisa existir
ls app.py spda/ dados/ng_municipios.csv

# 5. confirme que NENHUM segredo está entrando
git status --short | grep secrets.toml && echo "PARE: segredo no commit" || echo "ok, sem segredos"

# 6. commit e push
git add -A
git commit -m "v2.0.0: reescrita conforme ABNT NBR 5419-2:2026

Corrige os 8 achados bloqueantes e 13 graves da auditoria do commit b6aec3e:
tabelas normativas como dados, probabilidades por zona, P_LD matricial pela
Tabela B.8, C_LD/C_LI declarativos, L_F/L_O separados por tipo de perda,
N_G exclusivamente do Anexo F, F_T de sistema crítico, e as regras
condicionais das notas da Tabela 2 e de C.3.4 derivadas do modelo.

Acrescenta 300 testes, laudo A4 com ART/CREA e memorial, projeto salvável,
comparação de cenários (D.2) e autenticação PBKDF2."

git push origin main
```

> **Se o passo 2 assustar:** ele apaga arquivos. Rode primeiro
> `find . -mindepth 1 -not -path './.git' -not -path './.git/*'` sozinho para
> ver a lista antes de acrescentar `-delete`. E como tudo está no histórico do
> git, nada se perde de verdade — `git checkout <commit-antigo> -- .` traz a v1
> de volta se precisar.

Depois do push, o GitHub Actions roda os 300 testes sozinho. A aba **Actions**
do repositório tem que mostrar ✅ verde. Se estiver vermelho, **não publique** —
o motor está reprovando na própria suíte.

---

## Etapa 3 — Criar o app no Community Cloud

1. Entre em <https://share.streamlit.io> com a conta GitHub `felipe3fv-hash`.
2. Autorize o Streamlit a acessar **repositórios privados** quando ele pedir —
   sem isso ele não enxerga o `App` depois da Etapa 1.
3. **Create app** → **Deploy a public app from GitHub** (o rótulo é esse mesmo;
   a privacidade se ajusta depois).
4. Preencha:

   | Campo | Valor |
   |---|---|
   | **Repository** | `felipe3fv-hash/App` |
   | **Branch** | `main` |
   | **Main file path** | `app.py` |
   | **App URL** | `spda-risk-pro` (ou outro subdomínio livre) |

---

## Etapa 4 — Advanced settings: versão do Python

Ainda na tela de deploy, clique em **Advanced settings** e selecione
**Python version 3.12** (é o padrão e é o que a CI testa). Deixe o campo
**Secrets** em branco por enquanto. Clique em **Save** e depois em **Deploy**.

O build leva alguns minutos. Quando terminar, o app abre na tela de entrada.
Vá na aba **Solicitar acesso**, preencha seus dados e credenciais, envie, e
abra **Código técnico da sua solicitação**. Copie o bloco — algo como:

```toml
[usuarios]
mariz = "pbkdf2_sha256$260000$c0FmL2...$9xKp1..."
```

Volte ao painel do Streamlit: **⋮ → Settings → Secrets**, cole o bloco, salve.
O app reinicia sozinho e você já entra pela aba **Entrar**.

Para que as solicitações dos seus clientes cheguem por e-mail, acrescente
também o bloco `[email]` nos mesmos segredos:

```toml
[email]
remetente    = "proriskapp@gmail.com"
senha_app    = "as 16 letras da senha de app do Gmail"
destinatario = "proriskapp@gmail.com"
```

A `senha_app` do Gmail não é a senha da conta: é uma senha de aplicativo de 16
caracteres, gerada em `myaccount.google.com/apppasswords`, e ela só existe se a
verificação em duas etapas estiver ativa na conta. Sem esse bloco o app segue
funcionando — a solicitação aparece na tela para o cliente encaminhar.

Os segredos ficam no painel do Streamlit, nunca no repositório — é por isso que
`.streamlit/secrets.toml` está no `.gitignore`. Para acrescentar um usuário
depois, gere outra credencial e acrescente a linha dentro do mesmo
`[usuarios]`.

---

## Etapa 5 — Restringir o acesso

No app publicado, canto superior direito → **Share** →
**"Only specific people can view this app"**. Depois adicione os e-mails de
quem pode entrar e clique em **Invite**. Cada convidado recebe o link.

> **Limite do plano gratuito:** só é permitido **um app privado por vez**. Para
> publicar um segundo app a partir de repositório privado, é preciso tornar
> este público ou excluí-lo.

Repare que há duas camadas independentes: o Community Cloud controla quem
**abre** a página; o login PBKDF2 controla quem **calcula e emite laudo**. Um
convidado sem usuário cadastrado vê apenas a tela de login.

---

## Etapa 6 — Conferir que subiu certo

Com o app no ar, verifique nesta ordem:

1. **Login** — senha errada recusa; cinco erros seguidos bloqueiam por 5 min.
   Se o app avisar que não há usuários cadastrados, o bloco de segredos não foi
   salvo ou está com erro de digitação — o app diz qual dos dois.
2. **Aba 2** — a caixa azul diz "A base embarcada tem 5.572 municípios".
   Se disser outro número ou der erro, o `dados/ng_municipios.csv` não subiu.
3. **Aba 2** — selecione PE → Petrolina. Tem que aparecer **N_G = 6**.
4. **Aba 6** com o projeto vazio — tem que aparecer
   "3 inconsistência(s) impedem a emissão do laudo".
5. Preencha um caso mínimo e **gere o PDF**. Confira o rodapé:
   `SPDA Risk Pro v2.0.0 · ABNT NBR 5419-2:2026 · impressão digital dos dados: …`

---

## Manutenção

**Atualizar o app:** `git push` na `main`. O Community Cloud redeploya sozinho
(no máximo cinco atualizações por minuto).

**Antes de todo push que toque no motor** — `spda/tabelas.py`,
`probabilidades.py`, `perdas.py`, `eventos.py` ou `analise.py`:

```bash
pytest -q                 # os 300 testes têm que passar
# e incremente VERSAO_MOTOR em spda/versao.py
```

A versão vai impressa em cada página de cada laudo. Dois laudos com versões
diferentes do motor não são comparáveis sem análise — é isso que torna um laudo
seu defensável três anos depois.

---

## Sobre usar o Community Cloud para vender

O plano gratuito serve bem para piloto, demonstração e uso próprio. Três
limitações que pesam num produto comercial:

- **Um app privado por vez.** Se quiser ambientes separados (produção e
  homologação, ou um app por cliente), o plano gratuito não comporta.
- **Sem SLA e apps hibernam** com inatividade — a primeira visita depois de um
  tempo parado demora para carregar.
- **Hospedagem nos Estados Unidos.** Para dado de cliente sob LGPD isso pede
  avaliação. Neste app o risco é baixo, porque nada é persistido no servidor:
  o projeto vive na sessão e sai como `.json` na máquina do usuário.

Quando passar de piloto para venda recorrente, o caminho natural é um container
próprio (Railway, Render, Fly.io ou uma VM) com domínio seu — o app roda igual,
já que nada nele depende do Community Cloud.
