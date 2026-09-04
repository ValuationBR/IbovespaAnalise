"""
ESTE É O ÚNICO SCRIPT QUE VOCÊ PRECISA RODAR NO DIA A DIA.

Ele executa, em ordem:
 1. coletar_dados.py        -> busca preço, market cap e CNPJ de TODAS as ~86
                                empresas do Ibovespa na brapi.dev (grátis)
 2. selecionar_top40.py     -> marca as 40 maiores por valor de mercado; só
                                elas passam pelos passos seguintes
 3. coletar_dividendos_b3.py -> busca dividendos/JCP das 40 selecionadas, direto do site da B3 (grátis)
 4. baixar_dados_cvm.py     -> baixa os arquivos oficiais de DRE/Balanço da CVM (grátis)
 5. processar_cvm.py        -> lê os arquivos da CVM e grava DRE/Balanço das 40 selecionadas
 6. calcular_indicadores.py -> recalcula os 15 indicadores + 5 extras das 40 selecionadas
 7. valuation.py            -> recalcula o preço-alvo pelos 3 métodos
 8. gerar_comentarios.py    -> gera o comentário automático de cada empresa
 9. coletar_noticias.py     -> busca notícias recentes de cada empresa (RSS gratuito)
 10. gerar_excel.py          -> gera o arquivo Excel final

Se você configurar o Agendador de Tarefas do Windows para rodar este
arquivo todo dia (veja PASSO_A_PASSO.txt), a base de dados e o Excel
ficam sempre atualizados sozinhos.
"""
import sys
import traceback
from datetime import datetime

import coletar_dados
import selecionar_top40
import coletar_dividendos_b3
import baixar_dados_cvm
import processar_cvm
import calcular_indicadores
import valuation
import gerar_comentarios
import coletar_noticias
import gerar_excel

LOG_PATH = "logs/atualizacao.log"


def registrar(mensagem):
    linha = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {mensagem}"
    print(linha)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(linha + "\n")


def rodar_etapa(nome, funcao):
    registrar(f"Iniciando etapa: {nome}")
    try:
        funcao()
        registrar(f"Etapa concluída: {nome}")
        return True
    except Exception:
        registrar(f"ERRO na etapa {nome}:\n{traceback.format_exc()}")
        return False


def main():
    registrar("===== INÍCIO DA ATUALIZAÇÃO DIÁRIA =====")
    ok1 = rodar_etapa("Coleta de preço/market cap/CNPJ/setor (brapi.dev)", coletar_dados.main)
    ok2 = rodar_etapa("Seleção das 40 maiores por valor de mercado", selecionar_top40.main)
    ok3 = rodar_etapa("Coleta de dividendos (site da B3)", coletar_dividendos_b3.main)
    ok4 = rodar_etapa("Download dos dados da CVM", baixar_dados_cvm.main)
    ok5 = rodar_etapa("Processamento do DRE/Balanço (CVM)", processar_cvm.main)
    ok6 = rodar_etapa("Cálculo de indicadores", calcular_indicadores.main)
    ok7 = rodar_etapa("Valuation (Graham/Bazin/DCF)", valuation.main)
    ok8 = rodar_etapa("Geração dos comentários automáticos", gerar_comentarios.main)
    ok9 = rodar_etapa("Coleta de notícias", coletar_noticias.main)
    ok10 = rodar_etapa("Geração do Excel", gerar_excel.main)

    if all([ok1, ok2, ok3, ok4, ok5, ok6, ok7, ok8, ok9, ok10]):
        registrar("===== ATUALIZAÇÃO CONCLUÍDA COM SUCESSO =====")
    else:
        registrar("===== ATUALIZAÇÃO CONCLUÍDA COM ERROS — veja acima quais etapas falharam =====")
        sys.exit(1)


if __name__ == "__main__":
    main()

