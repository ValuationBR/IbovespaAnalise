"""
Lê os arquivos baixados da CVM (baixar_dados_cvm.py) e grava, para cada
empresa do Ibovespa (identificada pelo CNPJ, coletado via brapi.dev),
os dados de DRE e Balanço Patrimonial no banco de dados.

Fonte: dados abertos da CVM (Demonstrações Financeiras Padronizadas - DFP,
e Informações Trimestrais - ITR). Prioriza dados CONSOLIDADOS (_con); se a
empresa não tiver demonstração consolidada, usa a INDIVIDUAL (_ind).

Sobre a Dívida Líquida e o EBITDA: a CVM não entrega esses dois valores
prontos (eles não são uma linha fixa do balanço). Este script os estima
somando as contas cujo nome contém os termos financeiros correspondentes
("Empréstimos e Financiamentos", "Caixa e Equivalentes de Caixa",
"Depreciação/Amortização"). Isso funciona bem para a maioria das empresas,
mas pode ficar em branco para bancos e seguradoras, que usam um plano de
contas contábil diferente (COSIF).
"""
import os
import re
import pandas as pd
import psycopg2.extras
from db import conectar

import config

PASTA_CACHE = "dados_cvm"

CODIGOS_NET_INCOME_PRIORITARIOS = ["3.11", "3.09"]


def _normalizar_cnpj(cnpj):
    if not cnpj:
        return None
    return re.sub(r"\D", "", str(cnpj))


def _ler_csv_cvm(caminho):
    if not os.path.exists(caminho):
        return None
    for encoding in ("latin1", "utf-8", "cp1252"):
        try:
            return pd.read_csv(caminho, sep=";", encoding=encoding, low_memory=False)
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    return None


def _carregar_demonstrativo(pasta, prefixo, ano, tipo):
    """tipo: 'con' (consolidado) ou 'ind' (individual)"""
    nome_arquivo = f"{prefixo}_cia_aberta_{tipo}_{ano}.csv"
    caminho = os.path.join(pasta, nome_arquivo)
    return _ler_csv_cvm(caminho)


def _linhas_empresa(df, cnpj_num):
    if df is None or df.empty:
        return None
    df = df.copy()
    df["CNPJ_NUM"] = df["CNPJ_CIA"].astype(str).str.replace(r"\D", "", regex=True)
    linhas = df[(df["CNPJ_NUM"] == cnpj_num) & (df["ORDEM_EXERC"] == "ÚLTIMO")]
    return linhas if not linhas.empty else None


def _fator_escala(linhas):
    """A CVM informa os valores em milhares (MIL) na maioria dos casos.
    Este fator converte para o valor cheio em Reais."""
    if linhas is None or linhas.empty or "ESCALA_MOEDA" not in linhas.columns:
        return 1000.0
    escala = str(linhas.iloc[0]["ESCALA_MOEDA"]).upper()
    return 1000.0 if "MIL" in escala else 1.0


def _valor_por_codigo(linhas, codigo):
    if linhas is None:
        return None
    achou = linhas[linhas["CD_CONTA"] == codigo]
    if achou.empty:
        return None
    return float(achou.iloc[0]["VL_CONTA"]) * _fator_escala(linhas)


def _soma_por_texto(linhas, *termos):
    if linhas is None:
        return None
    padrao = "|".join(termos)
    achou = linhas[linhas["DS_CONTA"].str.contains(padrao, case=False, regex=True, na=False)]
    if achou.empty:
        return None
    return float(achou["VL_CONTA"].sum()) * _fator_escala(linhas)


def _lucro_liquido(linhas):
    for codigo in CODIGOS_NET_INCOME_PRIORITARIOS:
        v = _valor_por_codigo(linhas, codigo)
        if v is not None:
            return v
    return None


def _ano_de_dt_refer(linhas):
    if linhas is None or linhas.empty:
        return None
    return pd.to_datetime(linhas.iloc[0]["DT_REFER"]).year


def _obter_demonstrativos_empresa(pasta_extraida, prefixo, ano, cnpj_num):
    """Tenta consolidado primeiro, cai para individual se não achar a empresa."""
    resultado = {}
    for sufixo in ("con", "ind"):
        bpa = _carregar_demonstrativo(pasta_extraida, prefixo, ano, f"BPA_{sufixo}")
        bpp = _carregar_demonstrativo(pasta_extraida, prefixo, ano, f"BPP_{sufixo}")
        dre = _carregar_demonstrativo(pasta_extraida, prefixo, ano, f"DRE_{sufixo}")
        dfc = _carregar_demonstrativo(pasta_extraida, prefixo, ano, f"DFC_MI_{sufixo}")

        linhas_bpa = _linhas_empresa(bpa, cnpj_num)
        linhas_bpp = _linhas_empresa(bpp, cnpj_num)
        linhas_dre = _linhas_empresa(dre, cnpj_num)
        linhas_dfc = _linhas_empresa(dfc, cnpj_num)

        if linhas_bpa is not None or linhas_dre is not None:
            resultado = {
                "bpa": linhas_bpa, "bpp": linhas_bpp, "dre": linhas_dre, "dfc": linhas_dfc,
                "fonte": sufixo,
            }
            return resultado
    return resultado


def processar_empresa(cur, ticker, cnpj):
    cnpj_num = _normalizar_cnpj(cnpj)
    if not cnpj_num:
        return

    pastas_dfp = sorted(
        d for d in os.listdir(PASTA_CACHE) if d.startswith("dfp_") and os.path.isdir(os.path.join(PASTA_CACHE, d))
    ) if os.path.isdir(PASTA_CACHE) else []

    for pasta in pastas_dfp:
        ano = int(pasta.split("_")[1])
        pasta_extraida = os.path.join(PASTA_CACHE, pasta)
        dados = _obter_demonstrativos_empresa(pasta_extraida, "dfp", ano, cnpj_num)
        if not dados:
            continue
        _gravar_dre_balanco(cur, ticker, ano, dados)

    # ITR do ano corrente/anterior sobrescreve com o dado mais recente disponível
    pastas_itr = sorted(
        d for d in os.listdir(PASTA_CACHE) if d.startswith("itr_") and os.path.isdir(os.path.join(PASTA_CACHE, d))
    ) if os.path.isdir(PASTA_CACHE) else []

    for pasta in pastas_itr:
        ano = int(pasta.split("_")[1])
        pasta_extraida = os.path.join(PASTA_CACHE, pasta)
        dados = _obter_demonstrativos_empresa(pasta_extraida, "itr", ano, cnpj_num)
        if not dados:
            continue
        _gravar_dre_balanco(cur, ticker, ano, dados)


def _gravar_dre_balanco(cur, ticker, ano, dados):
    linhas_bpa = dados.get("bpa")
    linhas_bpp = dados.get("bpp")
    linhas_dre = dados.get("dre")
    linhas_dfc = dados.get("dfc")

    if linhas_dre is not None:
        receita = _valor_por_codigo(linhas_dre, "3.01")
        lucro_bruto = _valor_por_codigo(linhas_dre, "3.03")
        ebit = _valor_por_codigo(linhas_dre, "3.05")
        lucro_liquido = _lucro_liquido(linhas_dre)
        d_e_a = _soma_por_texto(linhas_dfc, "epreciaç", "mortizaç", "xaustão") if linhas_dfc is not None else None
        ebitda = (ebit + d_e_a) if (ebit is not None and d_e_a is not None) else ebit

        cur.execute(
            """INSERT INTO dre_anual (ticker, ano_fiscal, receita_total, lucro_bruto, ebitda, lucro_liquido, atualizado_em)
               VALUES (%s,%s,%s,%s,%s,%s, NOW())
               ON CONFLICT (ticker, ano_fiscal) DO UPDATE SET
                  receita_total = EXCLUDED.receita_total,
                  lucro_bruto = EXCLUDED.lucro_bruto,
                  ebitda = EXCLUDED.ebitda,
                  lucro_liquido = EXCLUDED.lucro_liquido,
                  atualizado_em = NOW()""",
            (ticker, ano, receita, lucro_bruto, ebitda, lucro_liquido),
        )

    if linhas_bpa is not None or linhas_bpp is not None:
        ativo_total = _valor_por_codigo(linhas_bpa, "1") if linhas_bpa is not None else None
        ativo_circulante = _valor_por_codigo(linhas_bpa, "1.01") if linhas_bpa is not None else None
        caixa = _soma_por_texto(linhas_bpa, "Caixa e Equivalentes de Caixa") if linhas_bpa is not None else None

        passivo_total = _valor_por_codigo(linhas_bpp, "2") if linhas_bpp is not None else None
        passivo_circulante = _valor_por_codigo(linhas_bpp, "2.01") if linhas_bpp is not None else None
        patrimonio_liquido = _valor_por_codigo(linhas_bpp, "2.03") if linhas_bpp is not None else None
        divida_bruta = _soma_por_texto(linhas_bpp, "Empréstimos e Financiamentos") if linhas_bpp is not None else None

        divida_liquida = None
        if divida_bruta is not None and caixa is not None:
            divida_liquida = divida_bruta - caixa

        cur.execute(
            """INSERT INTO balanco_anual
               (ticker, ano_fiscal, ativo_total, passivo_total, patrimonio_liquido,
                divida_liquida, ativo_circulante, passivo_circulante, atualizado_em)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s, NOW())
               ON CONFLICT (ticker, ano_fiscal) DO UPDATE SET
                  ativo_total = EXCLUDED.ativo_total,
                  passivo_total = EXCLUDED.passivo_total,
                  patrimonio_liquido = EXCLUDED.patrimonio_liquido,
                  divida_liquida = EXCLUDED.divida_liquida,
                  ativo_circulante = EXCLUDED.ativo_circulante,
                  passivo_circulante = EXCLUDED.passivo_circulante,
                  atualizado_em = NOW()""",
            (ticker, ano, ativo_total, passivo_total, patrimonio_liquido, divida_liquida,
             ativo_circulante, passivo_circulante),
        )


def main():
    if not os.path.isdir(PASTA_CACHE) or not os.listdir(PASTA_CACHE):
        print("Nenhum dado da CVM encontrado. Rode primeiro: python baixar_dados_cvm.py")
        return

    conn = conectar()
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT ticker, nome, cnpj FROM empresas WHERE selecionada = TRUE ORDER BY ticker")
    empresas = cur.fetchall()

    total = len(empresas)
    for i, emp in enumerate(empresas, start=1):
        if not emp["cnpj"]:
            print(f"[{i}/{total}] {emp['ticker']}: sem CNPJ ainda (rode coletar_dados.py primeiro), pulando.")
            continue
        print(f"[{i}/{total}] Processando {emp['ticker']} - {emp['nome']}...")
        try:
            processar_empresa(cur, emp["ticker"], emp["cnpj"])
        except Exception as e:
            print(f"   -> ERRO em {emp['ticker']}: {e}")
            cur.execute(
                "INSERT INTO log_execucao (etapa, ticker, status, mensagem) VALUES (%s,%s,%s,%s)",
                ("cvm", emp["ticker"], "ERRO", str(e)[:500]),
            )

    cur.close()
    conn.close()
    print("Processamento dos dados da CVM finalizado.")


if __name__ == "__main__":
    main()
