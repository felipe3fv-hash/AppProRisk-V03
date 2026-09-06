"""Identificação do motor de cálculo.

A versão é impressa em todo laudo emitido. Ela existe para que um laudo
questionado anos depois possa ser reproduzido exatamente com o mesmo motor.
Regra: qualquer alteração em `tabelas.py`, `probabilidades.py`, `perdas.py`,
`eventos.py` ou `analise.py` OBRIGA incremento de MINOR (ou MAJOR).
"""

VERSAO_MOTOR = "2.0.0"

# Versão do PRODUTO (interface, laudo, fluxo de acesso). Pode subir sem que o
# motor mude — e nesse caso os laudos continuam comparáveis entre si, porque o
# que o documento carrega é VERSAO_MOTOR.
VERSAO_APP = "2.1.0"
NORMA_APLICADA = "ABNT NBR 5419-2:2026 (2ª edição, 10.03.2026)"
NOME_PRODUTO = "SPDA Risk Pro"

__all__ = ["VERSAO_MOTOR", "VERSAO_APP", "NORMA_APLICADA", "NOME_PRODUTO"]
