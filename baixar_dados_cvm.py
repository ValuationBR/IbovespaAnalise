"""
Baixa da CVM (Comissão de Valores Mobiliários) os arquivos oficiais com a
DRE e o Balanço Patrimonial de TODAS as empresas de capital aberto do Brasil.
Fonte 100% gratuita e oficial: https://dados.cvm.gov.br

Baixa dois conjuntos, por ano:
 - DFP (Demonstrações Financeiras Padronizadas) = dados ANUAIS definitivos
 - ITR (Informações Trimestrais) = dados do trimestre mais recente do ano
   corrente (usados para não esperar o fechamento do ano todo)

Os arquivos ficam guardados em cache na pasta dados_cvm/. Anos antigos não
são baixados de novo (não mudam mais). O ano atual e o anterior são sempre
rebaixados, pois a CVM pode ter recebido novas entregas/retificações.
"""
import os
import zipfile
import requests
from datetime import date

import config

PASTA_CACHE = "dados_cvm"
ANO_INICIAL = 2020
URL_DFP = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip"
URL_ITR = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/itr_cia_aberta_{ano}.zip"


def baixar_e_extrair(url, ano, prefixo):
    nome_zip = os.path.join(PASTA_CACHE, f"{prefixo}_{ano}.zip")
    pasta_extraida = os.path.join(PASTA_CACHE, f"{prefixo}_{ano}")

    ano_atual = date.today().year
    ja_existe = os.path.isdir(pasta_extraida) and os.listdir(pasta_extraida)
    # anos "fechados" (mais de 1 ano no passado) não mudam mais: usa o cache se já existir
    if ja_existe and ano < ano_atual - 1:
        print(f"  {prefixo.upper()} {ano}: já em cache, pulando download.")
        return pasta_extraida

    print(f"  {prefixo.upper()} {ano}: baixando de {url} ...")
    try:
        resp = requests.get(url, timeout=120)
        if resp.status_code == 404:
            print(f"  {prefixo.upper()} {ano}: ainda não disponível na CVM (404), pulando.")
            return None
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  {prefixo.upper()} {ano}: erro ao baixar ({e}), pulando.")
        return None

    os.makedirs(PASTA_CACHE, exist_ok=True)
    with open(nome_zip, "wb") as f:
        f.write(resp.content)

    os.makedirs(pasta_extraida, exist_ok=True)
    with zipfile.ZipFile(nome_zip, "r") as z:
        z.extractall(pasta_extraida)

    print(f"  {prefixo.upper()} {ano}: OK ({len(resp.content)//1024} KB)")
    return pasta_extraida


def main():
    os.makedirs(PASTA_CACHE, exist_ok=True)
    ano_atual = date.today().year

    print("Baixando dados anuais (DFP) da CVM...")
    for ano in range(ANO_INICIAL, ano_atual + 1):
        baixar_e_extrair(URL_DFP.format(ano=ano), ano, "dfp")

    print("Baixando dados trimestrais (ITR) da CVM (para atualizar o ano corrente)...")
    for ano in (ano_atual - 1, ano_atual):
        baixar_e_extrair(URL_ITR.format(ano=ano), ano, "itr")

    print("Download da CVM finalizado.")


if __name__ == "__main__":
    main()
