"""
Recalcula, de forma consistente, os indicadores fundamentalistas de cada
empresa selecionada (as 40 maiores por valor de mercado), combinando:
 - preço atual e valor de mercado, vindos da brapi.dev (grátis)
 - receita, lucros, ativos, patrimônio, dívida, vindos da CVM (grátis)
 - histórico de preços acumulado no próprio banco (precos_diarios)

15 indicadores "clássicos":
 P/L, P/VP, ROE, ROIC, ROA, Dividend Yield, Margem Bruta, Margem Líquida,
 Margem EBITDA, Liquidez Corrente, Dívida Líquida/EBITDA, EV/EBITDA,
 EV/Receita, Payout, Giro do Ativo

+ 5 indicadores extras escolhidos para complementar a análise:
 - Variação em 12 meses do preço
 - Correlação com a carteira das 40 selecionadas (proxy do Ibovespa,
   calculada com os próprios dados coletados — não é a correlação oficial
   com o índice, mas uma aproximação com a mesma cesta de ações)
 - Correlação com o setor (média das outras empresas do mesmo setor)
 - Volatilidade anualizada (risco)
 - Beta em relação à carteira das 40 selecionadas
 - CAGR da Receita (crescimento anual composto, usando os anos disponíveis
   na CVM)

Observação sobre correlação/beta/volatilidade: como o histórico de preços
começa a ser acumulado a partir de agora (limite do plano gratuito da
brapi.dev), esses indicadores ficam mais confiáveis com o passar dos
dias — nas primeiras semanas eles usam poucos pontos de dados.
"""
import math
from datetime import date, timedelta
import psycopg2.extras
from db import conectar
import config


def div(a, b):
    try:
        if a is None or b is None or b == 0:
            return None
        return float(a) / float(b)
    except (TypeError, ZeroDivisionError):
        return None


def buscar_ultimo_ano(cur, tabela, ticker):
    cur.execute(f"SELECT * FROM {tabela} WHERE ticker=%s ORDER BY ano_fiscal DESC LIMIT 1", (ticker,))
    return cur.fetchone()


def buscar_dividendos_12m(cur, ticker):
    cur.execute(
        """SELECT COALESCE(SUM(valor),0) AS total FROM dividendos
           WHERE ticker=%s AND data_pagamento >= (CURRENT_DATE - INTERVAL '12 months')""",
        (ticker,),
    )
    row = cur.fetchone()
    return float(row["total"]) if row and row["total"] else 0.0


def _cagr_receita(cur, ticker):
    cur.execute(
        "SELECT ano_fiscal, receita_total FROM dre_anual WHERE ticker=%s ORDER BY ano_fiscal",
        (ticker,),
    )
    linhas = [r for r in cur.fetchall() if r["receita_total"] and float(r["receita_total"]) > 0]
    if len(linhas) < 2:
        return None
    primeiro, ultimo = linhas[0], linhas[-1]
    anos = ultimo["ano_fiscal"] - primeiro["ano_fiscal"]
    if anos <= 0:
        return None
    razao = float(ultimo["receita_total"]) / float(primeiro["receita_total"])
    if razao <= 0:
        return None
    return razao ** (1 / anos) - 1


def _series_precos(cur, ticker):
    cur.execute(
        "SELECT data_pregao, preco_fechamento FROM precos_diarios WHERE ticker=%s ORDER BY data_pregao",
        (ticker,),
    )
    return {r["data_pregao"]: float(r["preco_fechamento"]) for r in cur.fetchall() if r["preco_fechamento"]}


def _retornos_diarios(serie):
    """serie: dict {data: preco}, ordenado. Retorna dict {data: retorno_%}"""
    datas = sorted(serie.keys())
    retornos = {}
    for anterior, atual in zip(datas, datas[1:]):
        if serie[anterior] and serie[anterior] != 0:
            retornos[atual] = (serie[atual] / serie[anterior]) - 1
    return retornos


def _correlacao(retornos_a, retornos_b):
    datas_comuns = sorted(set(retornos_a) & set(retornos_b))
    if len(datas_comuns) < 10:
        return None
    xs = [retornos_a[d] for d in datas_comuns]
    ys = [retornos_b[d] for d in datas_comuns]
    n = len(xs)
    media_x = sum(xs) / n
    media_y = sum(ys) / n
    cov = sum((x - media_x) * (y - media_y) for x, y in zip(xs, ys)) / n
    var_x = sum((x - media_x) ** 2 for x in xs) / n
    var_y = sum((y - media_y) ** 2 for y in ys) / n
    if var_x == 0 or var_y == 0:
        return None
    return cov / math.sqrt(var_x * var_y)


def _beta(retornos_ativo, retornos_mercado):
    datas_comuns = sorted(set(retornos_ativo) & set(retornos_mercado))
    if len(datas_comuns) < 10:
        return None
    xs = [retornos_mercado[d] for d in datas_comuns]  # mercado = variável independente
    ys = [retornos_ativo[d] for d in datas_comuns]
    n = len(xs)
    media_x = sum(xs) / n
    media_y = sum(ys) / n
    cov = sum((x - media_x) * (y - media_y) for x, y in zip(xs, ys)) / n
    var_x = sum((x - media_x) ** 2 for x in xs) / n
    if var_x == 0:
        return None
    return cov / var_x


def _volatilidade_anualizada(retornos):
    valores = list(retornos.values())
    if len(valores) < 10:
        return None
    media = sum(valores) / len(valores)
    variancia = sum((v - media) ** 2 for v in valores) / len(valores)
    desvio_diario = math.sqrt(variancia)
    return desvio_diario * math.sqrt(252)


def _variacao_12m(serie):
    if not serie:
        return None
    datas = sorted(serie.keys())
    hoje = datas[-1]
    preco_atual = serie[hoje]
    alvo = hoje - timedelta(days=365)
    # pega a data mais próxima (para trás) de 365 dias atrás; se não houver
    # histórico tão antigo ainda, usa a primeira data disponível (melhor
    # esforço enquanto o histórico ainda está sendo acumulado)
    candidatas = [d for d in datas if d <= alvo]
    data_base = candidatas[-1] if candidatas else datas[0]
    preco_base = serie[data_base]
    if not preco_base:
        return None
    return (preco_atual / preco_base) - 1


def main():
    conn = conectar()
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT ticker, setor FROM empresas WHERE selecionada = TRUE ORDER BY ticker")
    empresas = cur.fetchall()
    tickers = [e["ticker"] for e in empresas]
    setor_por_ticker = {e["ticker"]: e["setor"] for e in empresas}

    # --- carrega séries de preço e retornos de todas as empresas selecionadas de uma vez ---
    series = {t: _series_precos(cur, t) for t in tickers}
    retornos = {t: _retornos_diarios(series[t]) for t in tickers}

    # carteira (proxy do Ibovespa): média simples dos retornos diários disponíveis
    todas_as_datas = sorted(set().union(*[set(r.keys()) for r in retornos.values()])) if retornos else []
    retorno_carteira = {}
    for d in todas_as_datas:
        valores_do_dia = [retornos[t][d] for t in tickers if d in retornos[t]]
        if len(valores_do_dia) >= 3:
            retorno_carteira[d] = sum(valores_do_dia) / len(valores_do_dia)

    for ticker in tickers:
        cur.execute("SELECT preco_atual, market_cap FROM indicadores WHERE ticker=%s", (ticker,))
        base = cur.fetchone()
        dre = buscar_ultimo_ano(cur, "dre_anual", ticker)
        bal = buscar_ultimo_ano(cur, "balanco_anual", ticker)
        dividendos_12m = buscar_dividendos_12m(cur, ticker)

        if not base or not base["preco_atual"]:
            continue

        preco = float(base["preco_atual"])
        market_cap = float(base["market_cap"]) if base["market_cap"] else None

        lucro_liquido = dre["lucro_liquido"] if dre else None
        receita = dre["receita_total"] if dre else None
        lucro_bruto = dre["lucro_bruto"] if dre else None
        ebitda = dre["ebitda"] if dre else None

        pl_liquido = bal["patrimonio_liquido"] if bal else None
        ativo_total = bal["ativo_total"] if bal else None
        divida_liquida = bal["divida_liquida"] if bal else None
        ativo_circ = bal["ativo_circulante"] if bal else None
        passivo_circ = bal["passivo_circulante"] if bal else None

        capital_investido = None
        if pl_liquido is not None and divida_liquida is not None:
            capital_investido = float(pl_liquido) + float(divida_liquida)

        ev = None
        if market_cap is not None and divida_liquida is not None:
            ev = market_cap + float(divida_liquida)

        # --- indicadores extras ---
        setor = setor_por_ticker.get(ticker)
        pares_do_setor = [t for t in tickers if t != ticker and setor_por_ticker.get(t) == setor and setor]
        retorno_setor = {}
        for d in todas_as_datas:
            valores_do_dia = [retornos[t][d] for t in pares_do_setor if d in retornos[t]]
            if valores_do_dia:
                retorno_setor[d] = sum(valores_do_dia) / len(valores_do_dia)

        variacao_12m = _variacao_12m(series[ticker])
        correlacao_carteira = _correlacao(retornos[ticker], retorno_carteira)
        correlacao_setor = _correlacao(retornos[ticker], retorno_setor) if retorno_setor else None
        volatilidade_anual = _volatilidade_anualizada(retornos[ticker])
        beta = _beta(retornos[ticker], retorno_carteira)
        cagr_receita = _cagr_receita(cur, ticker)

        indicadores = {
            "pl": div(market_cap, lucro_liquido),
            "pvp": div(market_cap, pl_liquido),
            "roe": div(lucro_liquido, pl_liquido),
            "roic": div(lucro_liquido, capital_investido),
            "roa": div(lucro_liquido, ativo_total),
            "dividend_yield": div(dividendos_12m, preco),
            "margem_bruta": div(lucro_bruto, receita),
            "margem_liquida": div(lucro_liquido, receita),
            "margem_ebitda": div(ebitda, receita),
            "liquidez_corrente": div(ativo_circ, passivo_circ),
            "divida_liquida_ebitda": div(divida_liquida, ebitda),
            "ev_ebitda": div(ev, ebitda),
            "ev_receita": div(ev, receita),
            "payout": div(dividendos_12m * (market_cap / preco) if market_cap and preco else None, lucro_liquido),
            "giro_ativo": div(receita, ativo_total),
        }

        cur.execute(
            """UPDATE indicadores SET
                 pl=%s, pvp=%s, roe=%s, roic=%s, roa=%s, dividend_yield=%s,
                 margem_bruta=%s, margem_liquida=%s, margem_ebitda=%s, liquidez_corrente=%s,
                 divida_liquida_ebitda=%s, ev_ebitda=%s, ev_receita=%s, payout=%s, giro_ativo=%s,
                 variacao_12m=%s, correlacao_carteira=%s, correlacao_setor=%s,
                 volatilidade_anual=%s, beta=%s, cagr_receita=%s,
                 atualizado_em=NOW()
               WHERE ticker=%s""",
            (
                indicadores["pl"], indicadores["pvp"], indicadores["roe"],
                indicadores["roic"], indicadores["roa"], indicadores["dividend_yield"],
                indicadores["margem_bruta"], indicadores["margem_liquida"], indicadores["margem_ebitda"],
                indicadores["liquidez_corrente"], indicadores["divida_liquida_ebitda"],
                indicadores["ev_ebitda"], indicadores["ev_receita"], indicadores["payout"],
                indicadores["giro_ativo"], variacao_12m, correlacao_carteira, correlacao_setor,
                volatilidade_anual, beta, cagr_receita, ticker,
            ),
        )

        cur.execute(
            """INSERT INTO indicadores_historico
               (ticker, data_calculo, preco_atual, market_cap, pl, pvp, roe, roic, roa,
                dividend_yield, margem_liquida, divida_liquida_ebitda, ev_ebitda, beta, volatilidade_anual)
               VALUES (%s, CURRENT_DATE, %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (ticker, data_calculo) DO UPDATE SET
                  preco_atual=EXCLUDED.preco_atual, market_cap=EXCLUDED.market_cap,
                  pl=EXCLUDED.pl, pvp=EXCLUDED.pvp, roe=EXCLUDED.roe, roic=EXCLUDED.roic,
                  roa=EXCLUDED.roa, dividend_yield=EXCLUDED.dividend_yield,
                  margem_liquida=EXCLUDED.margem_liquida, divida_liquida_ebitda=EXCLUDED.divida_liquida_ebitda,
                  ev_ebitda=EXCLUDED.ev_ebitda, beta=EXCLUDED.beta, volatilidade_anual=EXCLUDED.volatilidade_anual""",
            (
                ticker, preco, market_cap, indicadores["pl"], indicadores["pvp"], indicadores["roe"],
                indicadores["roic"], indicadores["roa"], indicadores["dividend_yield"],
                indicadores["margem_liquida"], indicadores["divida_liquida_ebitda"],
                indicadores["ev_ebitda"], beta, volatilidade_anual,
            ),
        )

    cur.close()
    conn.close()
    print("Indicadores (15 + 5 extras) recalculados para as empresas selecionadas.")


if __name__ == "__main__":
    main()
