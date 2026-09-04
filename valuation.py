"""
Calcula o preço-alvo de cada ação por 3 métodos de valuation:

 1. Fórmula de Graham   -> preço justo = sqrt(22.5 * LPA * VPA)
    (clássico, bom para empresas maduras e lucrativas)

 2. Método de Bazin     -> preço teto = dividendo pago nos últimos 12 meses / 6%
    (focado em geração de dividendos, bom para "pagadoras de dividendos")

 3. Fluxo de Caixa Descontado simplificado (DCF - modelo de perpetuidade de Gordon)
    -> valor da empresa = FCF projetado / (taxa de desconto - crescimento na perpetuidade)
    -> preço alvo = valor da empresa / nº de ações (estimado via marketCap / preço atual)

O preço-alvo médio é a média simples dos 3 métodos (quando disponíveis).
Todos os valores são recalculados sempre que novos dados chegam pela coleta diária.

Este script também guarda, todo dia, um "retrato" do preço-alvo médio de
cada empresa na tabela valuation_historico. Com isso dá para calcular a
variação do preço-alvo médio nos últimos 12 meses (como ele mudou ao
longo do tempo, e não só o valor de hoje) — assim como acontece com o
preço da ação, essa variação fica mais precisa conforme os dias passam.
"""
import math
from datetime import date, timedelta
import psycopg2.extras
from db import conectar
import config


def graham(lpa, vpa):
    try:
        if lpa is None or vpa is None or lpa <= 0 or vpa <= 0:
            return None
        return math.sqrt(22.5 * float(lpa) * float(vpa))
    except (TypeError, ValueError):
        return None


def bazin(dividendos_12m, dy_minimo):
    try:
        if not dividendos_12m or dividendos_12m <= 0:
            return None
        return float(dividendos_12m) / dy_minimo
    except (TypeError, ZeroDivisionError):
        return None


def dcf_simplificado(fcf_estimado, num_acoes, taxa_desconto, crescimento):
    try:
        if not fcf_estimado or not num_acoes or num_acoes <= 0:
            return None
        if taxa_desconto <= crescimento:
            return None
        valor_empresa = (float(fcf_estimado) * (1 + crescimento)) / (taxa_desconto - crescimento)
        return valor_empresa / float(num_acoes)
    except (TypeError, ZeroDivisionError):
        return None


def _variacao_alvo_12m(cur, ticker, preco_alvo_hoje):
    if not preco_alvo_hoje:
        return None
    cur.execute(
        "SELECT data_calculo, preco_alvo_medio FROM valuation_historico WHERE ticker=%s ORDER BY data_calculo",
        (ticker,),
    )
    linhas = [r for r in cur.fetchall() if r["preco_alvo_medio"]]
    if not linhas:
        return None
    alvo = date.today() - timedelta(days=365)
    candidatas = [r for r in linhas if r["data_calculo"] <= alvo]
    base = candidatas[-1] if candidatas else linhas[0]
    preco_base = float(base["preco_alvo_medio"])
    if not preco_base:
        return None
    return (float(preco_alvo_hoje) / preco_base) - 1


def main():
    conn = conectar()
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT ticker FROM empresas WHERE selecionada = TRUE ORDER BY ticker")
    tickers = [r["ticker"] for r in cur.fetchall()]

    for ticker in tickers:
        cur.execute("SELECT * FROM indicadores WHERE ticker=%s", (ticker,))
        ind = cur.fetchone()
        cur.execute(
            "SELECT * FROM balanco_anual WHERE ticker=%s ORDER BY ano_fiscal DESC LIMIT 1", (ticker,)
        )
        bal = cur.fetchone()
        cur.execute(
            "SELECT * FROM dre_anual WHERE ticker=%s ORDER BY ano_fiscal DESC LIMIT 1", (ticker,)
        )
        dre = cur.fetchone()
        cur.execute(
            """SELECT COALESCE(SUM(valor),0) AS total FROM dividendos
               WHERE ticker=%s AND data_pagamento >= (CURRENT_DATE - INTERVAL '12 months')""",
            (ticker,),
        )
        dividendos_12m = float(cur.fetchone()["total"] or 0)

        if not ind or not ind["preco_atual"]:
            continue

        preco_atual = float(ind["preco_atual"])
        market_cap = float(ind["market_cap"]) if ind["market_cap"] else None

        # LPA (lucro por ação) e VPA (valor patrimonial por ação): lucro/patrimônio total (CVM) / nº de ações
        num_acoes = (market_cap / preco_atual) if market_cap and preco_atual else None
        lpa = (float(dre["lucro_liquido"]) / num_acoes) if (dre and dre["lucro_liquido"] and num_acoes) else None
        vpa = (float(bal["patrimonio_liquido"]) / num_acoes) if (bal and bal["patrimonio_liquido"] and num_acoes) else None

        # FCF aproximado: usamos EBITDA - 20% (proxy simples de capex/impostos) quando não há
        # o dado de fluxo de caixa livre diretamente disponível.
        fcf_estimado = None
        if dre and dre["ebitda"]:
            fcf_estimado = float(dre["ebitda"]) * 0.75

        preco_graham = graham(lpa, vpa)
        preco_bazin = bazin(dividendos_12m, config.DY_MINIMO_BAZIN)
        preco_dcf = dcf_simplificado(
            fcf_estimado, num_acoes, config.TAXA_DESCONTO_DCF, config.CRESCIMENTO_PERPETUO
        )

        precos_validos = [p for p in [preco_graham, preco_bazin, preco_dcf] if p]
        preco_medio = sum(precos_validos) / len(precos_validos) if precos_validos else None
        upside = (preco_medio / preco_atual) - 1 if preco_medio and preco_atual else None
        variacao_alvo_12m = _variacao_alvo_12m(cur, ticker, preco_medio)

        cur.execute(
            """INSERT INTO valuation
               (ticker, preco_atual, preco_alvo_graham, preco_alvo_bazin, preco_alvo_dcf,
                preco_alvo_medio, upside_medio_pct, variacao_alvo_medio_12m, atualizado_em)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s, NOW())
               ON CONFLICT (ticker) DO UPDATE SET
                  preco_atual = EXCLUDED.preco_atual,
                  preco_alvo_graham = EXCLUDED.preco_alvo_graham,
                  preco_alvo_bazin = EXCLUDED.preco_alvo_bazin,
                  preco_alvo_dcf = EXCLUDED.preco_alvo_dcf,
                  preco_alvo_medio = EXCLUDED.preco_alvo_medio,
                  upside_medio_pct = EXCLUDED.upside_medio_pct,
                  variacao_alvo_medio_12m = EXCLUDED.variacao_alvo_medio_12m,
                  atualizado_em = NOW()""",
            (ticker, preco_atual, preco_graham, preco_bazin, preco_dcf, preco_medio, upside, variacao_alvo_12m),
        )

        if preco_medio:
            cur.execute(
                """INSERT INTO valuation_historico (ticker, data_calculo, preco_alvo_medio)
                   VALUES (%s, CURRENT_DATE, %s)
                   ON CONFLICT (ticker, data_calculo) DO UPDATE SET preco_alvo_medio = EXCLUDED.preco_alvo_medio""",
                (ticker, preco_medio),
            )

    cur.close()
    conn.close()
    print("Valuation (Graham, Bazin, DCF) recalculado para todas as empresas.")


if __name__ == "__main__":
    main()
