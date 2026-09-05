"""
Coleta, para cada empresa do Ibovespa, na API brapi.dev (plano GRATUITO):
 - CNPJ e dados cadastrais (módulo summaryProfile, gratuito) -> usado para
   cruzar com os dados da CVM (DRE e Balanço, veja processar_cvm.py)
 - histórico de preços diários (limitado a 3 meses por chamada no plano
   gratuito; a cada execução diária, os dias novos vão se acumulando no
   banco de dados, então o histórico completo cresce com o tempo)
 - preço atual e valor de mercado (marketCap), que são campos gratuitos
   sempre presentes na resposta

Os dividendos NÃO vêm mais daqui (o parâmetro "dividends=true" da brapi.dev
também passou a exigir plano pago). Eles são coletados à parte, direto do
site da B3, pelo script coletar_dividendos_b3.py.

Os dados de DRE e Balanço Patrimonial também não vêm daqui: são coletados
separadamente de graça direto na CVM (baixar_dados_cvm.py e processar_cvm.py).
"""
import time
import requests
from db import conectar
from datetime import datetime

import config
from lista_empresas import EMPRESAS_IBOVESPA

BASE_URL = "https://brapi.dev/api/quote/{ticker}"
MODULOS_GRATUITOS = "summaryProfile"


def log(cur, etapa, ticker, status, mensagem=""):
    cur.execute(
        "INSERT INTO log_execucao (etapa, ticker, status, mensagem) VALUES (%s,%s,%s,%s)",
        (etapa, ticker, status, mensagem[:500]),
    )


def buscar_dados_ticker(ticker):
    """Chama a API brapi.dev (recursos gratuitos) para um ticker e devolve o JSON."""
    params = {
        "token": config.BRAPI_TOKEN,
        "modules": MODULOS_GRATUITOS,
        "range": "3mo",   # plano gratuito só permite: 1d, 5d, 1mo, 3mo
        "interval": "1d",
    }
    resp = requests.get(BASE_URL.format(ticker=ticker), params=params, timeout=30)
    if resp.status_code >= 400:
        try:
            corpo = resp.json()
            detalhe = corpo.get("message") or corpo.get("error") or resp.text
        except ValueError:
            detalhe = resp.text
        raise ValueError(f"HTTP {resp.status_code}: {detalhe}")
    data = resp.json()
    resultados = data.get("results", [])
    if not resultados:
        raise ValueError("API não retornou dados para este ticker")
    return resultados[0]


def salvar_cnpj(cur, ticker, acao):
    perfil = acao.get("summaryProfile") or {}
    cnpj = perfil.get("cnpj")
    setor = perfil.get("sector") or perfil.get("industry")
    logo_url = acao.get("logourl") or acao.get("logoUrl") or acao.get("logo")
    if cnpj:
        cur.execute("UPDATE empresas SET cnpj=%s WHERE ticker=%s", (cnpj, ticker))
    if setor:
        cur.execute("UPDATE empresas SET setor=%s WHERE ticker=%s", (setor, ticker))
    if logo_url:
        cur.execute("UPDATE empresas SET logo_url=%s WHERE ticker=%s", (logo_url, ticker))


def salvar_precos(cur, ticker, acao):
    historico = acao.get("historicalDataPrice") or []
    for ponto in historico:
        ts = ponto.get("date")
        preco = ponto.get("close")
        if ts is None or preco is None:
            continue
        data_pregao = datetime.utcfromtimestamp(ts).date()
        cur.execute(
            """INSERT INTO precos_diarios (ticker, data_pregao, preco_fechamento)
               VALUES (%s,%s,%s)
               ON CONFLICT (ticker, data_pregao)
               DO UPDATE SET preco_fechamento = EXCLUDED.preco_fechamento""",
            (ticker, data_pregao, preco),
        )
    preco_atual = acao.get("regularMarketPrice")
    if preco_atual:
        cur.execute(
            """INSERT INTO precos_diarios (ticker, data_pregao, preco_fechamento)
               VALUES (%s, CURRENT_DATE, %s)
               ON CONFLICT (ticker, data_pregao)
               DO UPDATE SET preco_fechamento = EXCLUDED.preco_fechamento""",
            (ticker, preco_atual),
        )


def _parse_data(valor):
    if not valor:
        return None
    try:
        from dateutil import parser as dateparser
        return dateparser.parse(str(valor)).date()
    except (ValueError, TypeError, ImportError):
        return None


def salvar_preco_e_marketcap(cur, ticker, acao):
    """Guarda preço atual, valor de mercado (marketCap) e variação diária,
    campos gratuitos sempre presentes na resposta da brapi.dev — usados
    depois pelo calcular_indicadores.py junto com os dados de DRE/Balanço
    da CVM."""
    variacao_pct = acao.get("regularMarketChangePercent")
    variacao_diaria = (variacao_pct / 100.0) if variacao_pct is not None else None
    cur.execute(
        """INSERT INTO indicadores (ticker, preco_atual, market_cap, variacao_diaria, atualizado_em)
           VALUES (%s,%s,%s,%s, NOW())
           ON CONFLICT (ticker) DO UPDATE SET
              preco_atual = EXCLUDED.preco_atual,
              market_cap = EXCLUDED.market_cap,
              variacao_diaria = EXCLUDED.variacao_diaria,
              atualizado_em = NOW()""",
        (ticker, acao.get("regularMarketPrice"), acao.get("marketCap"), variacao_diaria),
    )


def main():
    conn = conectar()
    conn.autocommit = True
    cur = conn.cursor()

    total = len(EMPRESAS_IBOVESPA)
    for i, (ticker, nome) in enumerate(EMPRESAS_IBOVESPA, start=1):
        print(f"[{i}/{total}] Coletando {ticker} - {nome}...")
        try:
            acao = buscar_dados_ticker(ticker)
            salvar_cnpj(cur, ticker, acao)
            salvar_precos(cur, ticker, acao)
            salvar_preco_e_marketcap(cur, ticker, acao)
            log(cur, "coleta", ticker, "OK")
        except Exception as e:
            print(f"   -> ERRO em {ticker}: {e}")
            log(cur, "coleta", ticker, "ERRO", str(e))
        time.sleep(1.2)  # respeita o limite de requisições do plano gratuito

    cur.close()
    conn.close()
    print("Coleta (brapi.dev) finalizada.")


if __name__ == "__main__":
    main()
