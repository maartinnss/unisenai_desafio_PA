# ==============================================================================
# UNIDADE CURRICULAR: PROJETO APLICADO I | SCHULZ S.A.
# AV 03 (MVP Parte 1) | Arquivo 05: script principal de demonstração
#
# Para executar:  python 05_main.py
#
# Roteiro:
#   1. Cria o banco e o esquema          4. UPDATE (correção de uma leitura)
#   2. Instancia os objetos de domínio   5. Tratamento de erros
#   3. Insere registros de teste         6. Consultas com JOIN e relatório
#
# Todos os nomes e valores abaixo são dados de teste fictícios.
# ==============================================================================
import importlib
import os
import sys

# O arquivo se chama '04_classes.py' e começa com dígito, então o 'import'
# comum não funciona. O importlib aceita qualquer nome de módulo.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
dominio = importlib.import_module("04_classes")

BancoDados = dominio.BancoDados
Tecnico = dominio.Tecnico
Equipamento = dominio.Equipamento
Medicao = dominio.Medicao
ErroValidacao = dominio.ErroValidacao
ErroPersistencia = dominio.ErroPersistencia

CAMINHO_BANCO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "mvp_schulz_calibracao.db")


def titulo(texto: str) -> None:
    print("\n" + "=" * 100)
    print(texto)
    print("=" * 100)


def cadastrar_dados_de_teste(bd: BancoDados) -> list:
    titulo("2 e 3. INSTANCIAÇÃO DOS OBJETOS E INSERÇÃO DE REGISTROS DE TESTE")

    tecnicos = [
        Tecnico("Carlos Eduardo Pereira", "MT1001", "carlos.pereira@teste.com.br",
                "Metrologia"),
        Tecnico("Ana Beatriz Souza", "MT1002", "ana.souza@teste.com.br",
                "Metrologia"),
        Tecnico("Rafael Lima Costa", "US2001", "rafael.costa@teste.com.br",
                "Usinagem"),
    ]
    for t in tecnicos:
        bd.inserir_tecnico(t)
        print(f"  [OK] {t}")

    equipamentos = [
        Equipamento("703.1208", "Dispositivo de Controle", "CDM", "DC-120"),
        Equipamento("703.1315", "Dispositivo de Controle", "Usifer", "UF-45"),
        Equipamento("500.011", "Padrão Anel Liso", "Mitutoyo", "177-290"),
        Equipamento("810.0042", "Paquímetro Digital", "Mitutoyo", "500-196"),  # sem medição
    ]
    for e in equipamentos:
        bd.inserir_equipamento(e)
        print(f"  [OK] {e}")

    carlos, ana, rafael = tecnicos
    disp1, disp2, anel, _paq = equipamentos

    # No construtor, tolerancia_min e tolerancia_max já são os limites absolutos.
    # Na fábrica a_partir_de_desvios, informa-se o nominal e os desvios -/+.
    medicoes = [
        Medicao(disp1.id_equipamento, carlos.id_tecnico, "Diâmetro",
                25.000, 24.950, 25.030, 25.012),                      # aprovada
        Medicao(disp1.id_equipamento, carlos.id_tecnico, "Planicidade",
                0.000, 0.000, 0.020, 0.035),                          # reprovada (acima)
        Medicao.a_partir_de_desvios(
            disp1.id_equipamento, ana.id_tecnico, "Posição",
            50.000, -0.050, +0.050, 49.949),                          # reprovada (abaixo)
        Medicao.a_partir_de_desvios(
            disp2.id_equipamento, ana.id_tecnico, "Diâmetro",
            10.000, -0.020, +0.030, "10,030"),                        # no limite, aprovada
        Medicao(disp2.id_equipamento, rafael.id_tecnico, "Altura",
                75.500, 75.400, 75.600, 75.512),                      # aprovada
        Medicao(anel.id_equipamento, ana.id_tecnico, "Diâmetro Interno",
                40.000, 39.995, 40.005, 40.002),                      # aprovada
        Medicao(anel.id_equipamento, carlos.id_tecnico, "Diâmetro Interno",
                40.000, 39.995, 40.005, 40.011),                      # reprovada
    ]
    for m in medicoes:
        bd.inserir_medicao(m)
        print(f"  [OK] {m}  desvio={m.desvio:+.3f}")

    return medicoes


def demonstrar_update(bd: BancoDados, medicao: Medicao) -> None:
    titulo("4. UPDATE: CORREÇÃO DE LEITURA (o status é recalculado automaticamente)")
    print(f"  Antes : id={medicao.id_medicao} obtido={medicao.valor_obtido} "
          f"-> {medicao.status_resultado}")
    medicao.valor_obtido = 0.015  # a leitura anterior (0.035) foi digitada errada
    bd.atualizar_medicao(medicao)
    recarregada = bd.buscar_medicao(medicao.id_medicao)
    print(f"  Depois: id={recarregada.id_medicao} obtido={recarregada.valor_obtido} "
          f"-> {recarregada.status_resultado} (lido de volta do banco)")

    tecnico = bd.buscar_tecnico_por_matricula("US2001")
    tecnico.setor = "Metrologia"
    bd.atualizar_tecnico(tecnico)
    print(f"  Técnico remanejado: {bd.buscar_tecnico(tecnico.id_tecnico)}")


def demonstrar_tratamento_de_erros(bd: BancoDados, id_tecnico: int,
                                   id_equipamento: int) -> None:
    titulo("5. TRATAMENTO DE ERROS (todos os casos abaixo devem ser bloqueados)")

    def tentar(descricao, acao):
        try:
            acao()
            print(f"  [FALHA] '{descricao}' NÃO foi bloqueado!")
        except ErroValidacao as e:
            print(f"  [BLOQUEADO na validação do domínio] {descricao}\n"
                  f"       {e}")
        except ErroPersistencia as e:
            print(f"  [BLOQUEADO pelo SQLite] {descricao}\n       {e}")

    tentar("E-mail sem formato válido",
           lambda: Tecnico("Fulano de Tal", "MT9999", "email-invalido", "Metrologia"))
    tentar("Valor obtido não numérico",
           lambda: Medicao(id_equipamento, id_tecnico, "Diâmetro", 10, 9.9, 10.1, "abc"))
    tentar("Limite inferior maior que o superior",
           lambda: Medicao(id_equipamento, id_tecnico, "Diâmetro", 10, 10.2, 10.1, 10))
    tentar("Nominal fora da faixa de tolerância",
           lambda: Medicao(id_equipamento, id_tecnico, "Diâmetro", 10, 10.1, 10.2, 10.15))
    tentar("Matrícula duplicada (UNIQUE)",
           lambda: bd.inserir_tecnico(
               Tecnico("Outro Nome", "MT1001", "outro@teste.com.br", "Metrologia")))
    tentar("Tag duplicada (UNIQUE)",
           lambda: bd.inserir_equipamento(
               Equipamento("703.1208", "Qualquer", "CDM", "X1")))
    tentar("Medição com equipamento inexistente (FOREIGN KEY)",
           lambda: bd.inserir_medicao(
               Medicao(9999, id_tecnico, "Diâmetro", 10, 9.9, 10.1, 10.0)))
    tentar("Excluir técnico que possui medições (ON DELETE RESTRICT)",
           lambda: bd.remover_tecnico(id_tecnico))
    tentar("Filtro de status inválido no relatório",
           lambda: bd.relatorio_calibracao(status="TALVEZ"))


def imprimir_relatorio(linhas: list, titulo_relatorio: str) -> None:
    titulo(titulo_relatorio)
    if not linhas:
        print("  (nenhum registro)")
        return
    cab = (f"{'ID':>3} | {'TAG':<9} | {'PARÂMETRO':<17} | {'NOMINAL':>8} | "
           f"{'LIM.MIN':>8} | {'LIM.MAX':>8} | {'OBTIDO':>8} | {'STATUS':<9} | "
           f"{'TÉCNICO':<22}")
    print(cab)
    print("-" * len(cab))
    for r in linhas:
        print(f"{r['id_medicao']:>3} | {r['codigo_tag']:<9} | "
              f"{r['parametro_medido']:<17} | {r['valor_nominal']:>8.3f} | "
              f"{r['tolerancia_min']:>8.3f} | {r['tolerancia_max']:>8.3f} | "
              f"{r['valor_obtido']:>8.3f} | {r['status_resultado']:<9} | "
              f"{r['nome_tecnico']:<22}")


def main() -> None:
    titulo("MVP PARTE 1: SISTEMA DE CALIBRAÇÃO | SCHULZ S.A. (dados de teste)")

    # O banco é recriado a cada execução para o resultado ser reproduzível.
    if os.path.exists(CAMINHO_BANCO):
        os.remove(CAMINHO_BANCO)

    try:
        with BancoDados(CAMINHO_BANCO) as bd:
            titulo("1. CONEXÃO E CRIAÇÃO DO ESQUEMA (tecnico, equipamento, medicao)")
            bd.criar_esquema()
            print(f"  Banco criado: {os.path.basename(CAMINHO_BANCO)}")

            medicoes = cadastrar_dados_de_teste(bd)
            demonstrar_update(bd, medicoes[1])  # planicidade: 0.035 para 0.015
            demonstrar_tratamento_de_erros(
                bd, medicoes[0].id_tecnico, medicoes[0].id_equipamento)

            imprimir_relatorio(bd.relatorio_calibracao(),
                               "6.1 RELATÓRIO DE CALIBRAÇÃO COMPLETO "
                               "(medicao JOIN equipamento JOIN tecnico)")
            imprimir_relatorio(bd.relatorio_calibracao(status="REPROVADO"),
                               "6.2 SOMENTE MEDIÇÕES REPROVADAS")
            imprimir_relatorio(bd.relatorio_calibracao(codigo_tag="703.1208"),
                               "6.3 HISTÓRICO DO EQUIPAMENTO 703.1208")

            titulo("6.4 RESUMO POR EQUIPAMENTO (LEFT JOIN com GROUP BY)")
            print(f"{'TAG':<10} | {'EQUIPAMENTO':<24} | {'TOTAL':>5} | "
                  f"{'APROV.':>6} | {'REPROV.':>7}")
            print("-" * 64)
            for r in bd.resumo_por_equipamento():
                print(f"{r['codigo_tag']:<10} | {r['nome_equipamento']:<24} | "
                      f"{r['total']:>5} | {r['aprovadas']:>6} | {r['reprovadas']:>7}")

        print("\nExecução concluída com sucesso.")
    except (ErroPersistencia, ErroValidacao) as e:
        print(f"\nERRO FATAL: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
