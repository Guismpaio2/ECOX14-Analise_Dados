"""Ponto de entrada para orquestrar o pipeline do projeto."""

import logging
import sys
import time

import config


log = logging.getLogger(__name__)


def etapa_ingestao():
    import ingerir

    ingerir.main()


def etapa_exploracao():
    import explorar

    explorar.main()


def etapa_transformacao():
    import transformar_gpu
    import transformar_llm

    transformar_gpu.main()
    transformar_llm.main()


ETAPAS = [
    ("ingestao", etapa_ingestao),
    ("exploracao", etapa_exploracao),
    ("transformacao", etapa_transformacao),
    ("carga", None),
    ("modelagem", None),
]


def executar(nome, funcao):
    log.info("etapa %s: inicio", nome)
    comeco = time.perf_counter()
    try:
        funcao()
    except Exception:
        log.exception("etapa %s falhou", nome)
        raise
    duracao = time.perf_counter() - comeco
    log.info("etapa %s: fim em %.0fs", nome, duracao)


def main(a_partir_de=None):
    config.configurar_log()
    config.criar_pastas()

    nomes = [nome for nome, _ in ETAPAS]
    if a_partir_de and a_partir_de not in nomes:
        log.error("etapa desconhecida: %s", a_partir_de)
        log.error("etapas validas: %s", ", ".join(nomes))
        return 1

    comecou = a_partir_de is None
    for nome, funcao in ETAPAS:
        if nome == a_partir_de:
            comecou = True
        if not comecou:
            log.info("etapa %s: pulada", nome)
            continue
        if funcao is None:
            log.warning("etapa %s: ainda nao implementada", nome)
            continue
        executar(nome, funcao)

    log.info("pipeline concluido")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
