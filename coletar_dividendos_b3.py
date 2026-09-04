"""
Busca o histórico de dividendos e JCP (Juros sobre Capital Próprio) de cada
empresa direto do site da B3 (b3.com.br), usando o mesmo endpoint público
que o site oficial usa para mostrar a página "Proventos em Dinheiro" de
cada empresa. É gratuito e não exige cadastro nem token.

IMPORTANTE: este é um endpoint PÚBLICO mas NÃO OFICIAL/NÃO DOCUMENTADO da
B3 (o próprio site da bolsa usa por trás dos panos). Por não ser um
contrato oficial, a B3 pode mudar o formato dessa resposta a qualquer
momento sem aviso, o que pode quebrar este script. Se isso acontecer, o
script vai logar o erro exato (em log_execucao) para conseguirmos ajustar.

Funciona em 2 passos, iguais aos que o próprio site da B3 faz ao abrir a
página de uma ação:
 1. GetInitialCompanies: acha o "tradingName" (código de 4 letras da
    empresa, ex: PETR) a partir do ticker (ex: PETR4).
 2. GetListedCashDividends: usa esse tradingName para buscar a lista de
    proventos em dinheiro (dividendos e JCP) já pagos ou aprovados.
"""
import time
import json
from base64 import b64encode
from datetime import datetime

import requests
from db import conectar

import config

URL_INITIAL_COMPANIES = "https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/GetInitialCompanies/{params}"
URL_CASH_DIVIDENDS = "https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/GetListedCashDividends/{params}"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PainelIbovespa/1.0)"}


def _codificar(params_dict):
    texto = json.dumps(params_dict)
    return b64encode(texto.encode("utf-8")).decode("utf-8")


def buscar_trading_name(ticker):
    """Descobre o código de 4 letras da empresa (ex: PETR4 -> PETR)."""
    codigo_base = ticker[:4]
    params = _codificar({"language": "pt-br", "pageNumber": 1, "pageSize": 20, "company": codigo_base})
    resp = requests.get(URL_INITIAL_COMPANIES.format(params=params), headers=HEADERS, timeout=30)
    resp.raise_for_status()
    dados = resp.json()
    for item in dados.get("results", []):
        if str(item.get("issuingCompany", "")).upper() == codigo_base.upper():
            return item.get("tradingName")
    # se não achou correspondência exata, usa o primeiro resultado (melhor esforço)
    resultados = dados.get("results", [])
    if resultados:
        return resultados[0].get("tradingName")
    return None


def buscar_dividendos(trading_name):
    params = _codificar({
        "language": "pt-br", "pageNumber": 1, "pageSize": 200, "tradingName": trading_name,
    })
    resp = requests.get(URL_CASH_DIVIDENDS.format(params=params), headers=HEADERS, timeout=30)
    resp.raise_for_status()
    dados = resp.json()
    return dados.get("results", [])


def diagnosticar_formato(cur, ticker, itens):
    """Grava no log, uma única vez por execução, as chaves e um exemplo
    do primeiro provento retornado — ajuda a corrigir o parsing se a B3
    mudar o formato da resposta (ou se os nomes de campo usados no
    parsing estiverem errados)."""
    if not itens:
        return
    primeiro = itens[0]
    amostra = {k: primeiro.get(k) for k in list(primeiro.keys())[:12]}
    cur.execute(
        "INSERT INTO log_execucao (etapa, ticker, status, mensagem) VALUES (%s,%s,%s,%s)",
        ("dividendos_b3_diagnostico", ticker, "INFO", str(amostra)[:500]),
    )


def _parse_data_br(valor):
    """A B3 costuma devolver datas como 'dd/mm/aaaa'."""
    if not valor:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(valor, fmt).date()
        except ValueError:
            continue
    return None


def _parse_valor_br(valor):
    if valor in (None, "", "-"):
        return None
    try:
        texto = str(valor).replace(".", "").replace(",", ".")
        return float(texto)
    except ValueError:
        return None


def salvar_dividendos(cur, ticker, itens):
    for item in itens:
        tipo = item.get("typeStock") or item.get("dividendType") or "PROVENTO"
        valor = _parse_valor_br(item.get("rate") or item.get("value"))
        data_com = _parse_data_br(item.get("lastDatePriorEx") or item.get("dateApproval"))
        data_pagamento = _parse_data_br(item.get("paymentDate") or item.get("dateClosingPrice"))
        if valor is None:
            continue
        cur.execute(
            """INSERT INTO dividendos (ticker, tipo, valor, data_pagamento, data_com)
               VALUES (%s,%s,%s,%s,%s)
               ON CONFLICT (ticker, tipo, valor, data_pagamento) DO NOTHING""",
            (ticker, tipo, valor, data_pagamento, data_com),
        )


def main():
    conn = conectar()
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("SELECT ticker, nome FROM empresas WHERE selecionada = TRUE ORDER BY ticker")
    empresas = cur.fetchall()

    total = len(empresas)
    for i, (ticker, nome) in enumerate(empresas, start=1):
        print(f"[{i}/{total}] Buscando dividendos de {ticker} - {nome}...")
        try:
            trading_name = buscar_trading_name(ticker)
            if not trading_name:
                raise ValueError("não foi possível identificar o código da empresa no site da B3")
            itens = buscar_dividendos(trading_name)
            if i == 1:  # loga o formato bruto só da primeira empresa, para não poluir o log
                diagnosticar_formato(cur, ticker, itens)
            salvar_dividendos(cur, ticker, itens)
            cur.execute(
                "INSERT INTO log_execucao (etapa, ticker, status, mensagem) VALUES (%s,%s,%s,%s)",
                ("dividendos_b3", ticker, "OK", f"{len(itens)} registros"),
            )
        except Exception as e:
            print(f"   -> ERRO em {ticker}: {e}")
            cur.execute(
                "INSERT INTO log_execucao (etapa, ticker, status, mensagem) VALUES (%s,%s,%s,%s)",
                ("dividendos_b3", ticker, "ERRO", str(e)[:500]),
            )
        time.sleep(0.8)

    cur.close()
    conn.close()
    print("Coleta de dividendos (B3) finalizada.")


if __name__ == "__main__":
    main()
