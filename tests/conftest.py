"""Shared fixtures for the test suite."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

SAMPLE_CONTRACT_TEXT = """\
CONTRATO FICTICIO DE PRESTACAO DE SERVICOS DE CONSULTORIA OPERACIONAL E TECNOLOGIA
Documento meramente ilustrativo, sem validade juridica, criado para fins de exemplo.

CLAUSULA 1 - DO OBJETO
O presente contrato tem por objeto a prestacao, pela CONTRATADA, de servicos de consultoria
operacional, automacao de processos, apoio em inteligencia de dados, levantamento de
requisitos, implantacao de fluxos digitais e treinamento de equipe para a CONTRATANTE.

CLAUSULA 2 - DO REGIME DE EXECUCAO
Os servicos serao executados em regime de prestacao de servicos autonomos entre pessoas
juridicas, sem qualquer relacao de emprego, subordinacao trabalhista, exclusividade pessoal
obrigatoria ou controle de jornada tipico de vinculo empregaticio.

CLAUSULA 3 - DO PRAZO DE VIGENCIA
O presente contrato vigorara pelo periodo de 12 (doze) meses, iniciando-se em 01 de agosto
de 2026 e encerrando-se em 31 de julho de 2027, podendo ser renovado mediante termo aditivo
assinado pelas partes.

CLAUSULA 4 - DO VALOR E FORMA DE PAGAMENTO
Pela execucao dos servicos, a CONTRATANTE pagara a CONTRATADA o valor mensal ficticio de
R$ 8.500,00 (oito mil e quinhentos reais), mediante emissao de nota fiscal. O pagamento
devera ocorrer ate o dia 10 (dez) de cada mes, por transferencia bancaria ou PIX empresarial.

CLAUSULA 5 - DO REAJUSTE
O valor mensal podera ser reajustado a cada 12 (doze) meses, tomando-se como referencia a
variacao acumulada do IPCA, ou outro indice que vier a substitui-lo.

CLAUSULA 6 - DAS MULTAS E PENALIDADES POR RESCISAO
Em caso de rescisao antecipada e imotivada por qualquer das partes, sera devida multa
compensatoria equivalente a 20% (vinte por cento) do valor total remanescente do contrato.

CLAUSULA 7 - DA CONFIDENCIALIDADE
As partes obrigam-se a manter sigilo absoluto sobre todas as informacoes tecnicas, comerciais
e estrategicas trocadas durante a vigencia deste contrato, por prazo de 5 (cinco) anos apos
seu termino.
"""


@pytest.fixture
def sample_contract_text() -> str:
    return SAMPLE_CONTRACT_TEXT


@pytest.fixture
def temp_chroma_dir() -> Iterator[str]:
    path = tempfile.mkdtemp(prefix="chroma_test_")
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def sample_pdf_path() -> Path:
    return Path(__file__).parent.parent / "contrato_exemplo.pdf"
