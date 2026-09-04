"""
Gera um comentário curto e automático para cada empresa, destacando os
indicadores que mais chamam atenção (positiva ou negativamente), com base
em faixas de referência usadas com frequência por investidores brasileiros.
Não é uma recomendação de compra/venda — é só um resumo objetivo dos
números para ajudar a interpretar a tabela mais rápido.
"""

# faixas de referência aproximadas (mercado brasileiro, uso geral)
FAIXAS = {
    "pl": {"baixo": 8, "alto": 20},
    "pvp": {"baixo": 1, "alto": 3},
    "roe": {"baixo": 0.08, "alto": 0.18},
    "roic": {"baixo": 0.08, "alto": 0.18},
    "dividend_yield": {"baixo": 0.03, "alto": 0.08},
    "divida_liquida_ebitda": {"baixo": 1.0, "alto": 3.5},
    "margem_liquida": {"baixo": 0.05, "alto": 0.20},
    "liquidez_corrente": {"baixo": 1.0, "alto": 2.0},
}


def gerar_comentario(ind, valuation, setor):
    pontos_positivos = []
    pontos_negativos = []

    def _n(v):
        return float(v) if v is not None else None

    pl = _n(ind.get("pl"))
    pvp = _n(ind.get("pvp"))
    roe = _n(ind.get("roe"))
    roic = _n(ind.get("roic"))
    dy = _n(ind.get("dividend_yield"))
    div_ebitda = _n(ind.get("divida_liquida_ebitda"))
    margem_liq = _n(ind.get("margem_liquida"))
    liquidez = _n(ind.get("liquidez_corrente"))
    payout = _n(ind.get("payout"))
    beta = _n(ind.get("beta"))
    cagr = _n(ind.get("cagr_receita"))

    if roe is not None:
        if roe >= FAIXAS["roe"]["alto"]:
            pontos_positivos.append(f"ROE elevado ({roe:.1%}), boa rentabilidade sobre o patrimônio")
        elif roe < FAIXAS["roe"]["baixo"]:
            pontos_negativos.append(f"ROE baixo ({roe:.1%})")

    if roic is not None:
        if roic >= FAIXAS["roic"]["alto"]:
            pontos_positivos.append(f"ROIC elevado ({roic:.1%}), bom retorno sobre o capital investido")
        elif roic < FAIXAS["roic"]["baixo"]:
            pontos_negativos.append(f"ROIC baixo ({roic:.1%})")

    if dy is not None:
        if dy >= FAIXAS["dividend_yield"]["alto"]:
            pontos_positivos.append(f"Dividend Yield alto ({dy:.1%}), boa pagadora de proventos")
        elif dy < FAIXAS["dividend_yield"]["baixo"]:
            pontos_negativos.append(f"Dividend Yield baixo ({dy:.1%})")

    if div_ebitda is not None:
        if div_ebitda > FAIXAS["divida_liquida_ebitda"]["alto"]:
            pontos_negativos.append(f"Endividamento elevado (Dív.Líq/EBITDA {div_ebitda:.1f}x)")
        elif div_ebitda < 0:
            pontos_positivos.append("Caixa líquido positivo (dívida líquida negativa)")
        elif div_ebitda <= FAIXAS["divida_liquida_ebitda"]["baixo"]:
            pontos_positivos.append(f"Endividamento baixo (Dív.Líq/EBITDA {div_ebitda:.1f}x)")

    if pl is not None and pl > 0:
        if pl < FAIXAS["pl"]["baixo"]:
            pontos_positivos.append(f"P/L baixo ({pl:.1f}x), pode indicar ação descontada")
        elif pl > FAIXAS["pl"]["alto"]:
            pontos_negativos.append(f"P/L elevado ({pl:.1f}x), preço caro em relação ao lucro atual")

    if pvp is not None and pvp > 0:
        if pvp < FAIXAS["pvp"]["baixo"]:
            pontos_positivos.append(f"Negociada abaixo do valor patrimonial (P/VP {pvp:.2f}x)")
        elif pvp > FAIXAS["pvp"]["alto"]:
            pontos_negativos.append(f"P/VP elevado ({pvp:.2f}x)")

    if margem_liq is not None:
        if margem_liq >= FAIXAS["margem_liquida"]["alto"]:
            pontos_positivos.append(f"Margem líquida forte ({margem_liq:.1%})")
        elif margem_liq < 0:
            pontos_negativos.append("Margem líquida negativa (empresa operando com prejuízo)")
        elif margem_liq < FAIXAS["margem_liquida"]["baixo"]:
            pontos_negativos.append(f"Margem líquida apertada ({margem_liq:.1%})")

    if liquidez is not None and liquidez < FAIXAS["liquidez_corrente"]["baixo"]:
        pontos_negativos.append(f"Liquidez corrente baixa ({liquidez:.2f})")

    if payout is not None and payout > 1:
        pontos_negativos.append(f"Payout acima de 100% ({payout:.0%}) — distribuiu mais do que lucrou")

    if beta is not None:
        if beta > 1.3:
            pontos_negativos.append(f"Beta alto ({beta:.2f}), ação mais volátil que a carteira")
        elif 0 < beta < 0.7:
            pontos_positivos.append(f"Beta baixo ({beta:.2f}), ação mais defensiva")

    if cagr is not None:
        if cagr >= 0.10:
            pontos_positivos.append(f"Receita crescendo forte (CAGR {cagr:.1%} ao ano)")
        elif cagr < 0:
            pontos_negativos.append(f"Receita em queda no período (CAGR {cagr:.1%} ao ano)")

    upside = valuation.get("upside_medio_pct") if valuation else None
    if upside is not None:
        upside = float(upside)
        if upside >= 0.20:
            pontos_positivos.append(f"Valuation sugere upside relevante ({upside:.0%})")
        elif upside <= -0.20:
            pontos_negativos.append(f"Valuation sugere ação esticada ({upside:.0%} de downside)")

    partes = []
    if pontos_positivos:
        partes.append("Pontos fortes: " + "; ".join(pontos_positivos[:3]) + ".")
    if pontos_negativos:
        partes.append("Pontos de atenção: " + "; ".join(pontos_negativos[:3]) + ".")
    if not partes:
        partes.append("Indicadores dentro de faixas normais, sem destaque relevante para mais ou para menos.")

    return " ".join(partes)
