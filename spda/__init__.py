"""Motor de análise de risco contra descargas atmosféricas — ABNT NBR 5419-2:2026.

Camadas, de baixo para cima:

    tabelas.py        tabelas normativas como dados (Anexos A, B, C, D)
    ng.py             Anexo F — N_G por município
    modelo.py         Projeto, Estrutura, Zona, Sistema interno, Linha, Trecho
    eventos.py        Anexo A — N_D, N_M, N_L, N_I, N_DJ
    probabilidades.py Anexo B — P_A … P_Z, com as eq. (12) e (13)
    perdas.py         Anexos C e D — L_X separado por tipo de perda
    analise.py        Seções 4.3, 6 e 7 — R1, R3, R4 e F, decompostos
    validacao.py      consistência dos dados de entrada
    laudo.py          emissão do PDF A4
    projeto_io.py     serialização, clonagem de cenários, hash dos dados
    auth.py           autenticação

Nenhum módulo de cálculo importa Streamlit. A interface é substituível.
"""

from .versao import NOME_PRODUTO, NORMA_APLICADA, VERSAO_MOTOR

__all__ = ["VERSAO_MOTOR", "NORMA_APLICADA", "NOME_PRODUTO"]
