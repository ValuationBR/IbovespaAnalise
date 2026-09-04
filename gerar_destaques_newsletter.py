"""
Gera um resumo em texto simples com os destaques da semana, prontos para
copiar e colar na newsletter. Roda a qualquer momento depois de
atualizar_tudo.py (não faz parte do pipeline automático — é para rodar
manualmente quando for escrever a edição da semana).

Uso:
    python gerar_destaques_newsletter.py

O resultado aparece no terminal E é salvo em:
    saida/Destaques_Semana.txt
"""
import os
from datetime import date
import psycopg2.extras
from db import conectar
import config

TOP_N = 3


def _consultar(cur, campo, ordem, minimo_nao_nulo=True):
    filtro = f"AND {campo} IS NOT NULL" if minimo_nao_nulo else ""
    cur.execute(
        f"""SELECT e.ticker, e.nome, e.setor, i.{campo}
           FROM empresas e JOIN indicadores i ON i.ticker = e.ticker
           WHERE e.selecionada = TRUE {filtro}
           ORDER BY i.{campo} {ordem}
           LIMIT %s""",
        (TOP_N,),
    )
    return cur.fetchall()


def _consultar_valuation(cur, campo, ordem):
    cur.execute(
        f"""SELECT e.ticker, e.nome, v.{campo}, v.preco_alvo_medio, v.preco_atual
           FROM empresas e JOIN valuation v ON v.ticker = e.ticker
           WHERE e.selecionada = TRUE AND v.{campo} IS NOT NULL
           ORDER BY v.{campo} {ordem}
           LIMIT %s""",
        (TOP_N,),
    )
    return cur.fetchall()


def _fmt_pct(v):
    return f"{float(v) * 100:.1f}%" if v is not None else "—"


def _fmt_moeda(v):
    return f"R$ {float(v):.2f}" if v is not None else "—"


def _linha(ticker, nome, valor_fmt, setor=None):
    setor_txt = f" ({setor})" if setor else ""
    return f"  • {ticker} — {nome}{setor_txt}: {valor_fmt}"


def montar_texto(cur):
    hoje = date.today().strftime("%d/%m/%Y")
    partes = []
    partes.append(f"DESTAQUES DA SEMANA — {hoje}")
    partes.append("=" * 50)
    partes.append("")

    partes.append("🔼 MAIOR UPSIDE (valuation médio vs. preço atual)")
    for r in _consultar_valuation(cur, "upside_medio_pct", "DESC"):
        partes.append(_linha(r["ticker"], r["nome"], _fmt_pct(r["upside_medio_pct"])))
    partes.append("")

    partes.append("🔽 MENOR UPSIDE / MAIS ESTICADAS")
    for r in _consultar_valuation(cur, "upside_medio_pct", "ASC"):
        partes.append(_linha(r["ticker"], r["nome"], _fmt_pct(r["upside_medio_pct"])))
    partes.append("")

    partes.append("💰 MAIOR DIVIDEND YIELD (últimos 12 meses)")
    for r in _consultar(cur, "dividend_yield", "DESC"):
        partes.append(_linha(r["ticker"], r["nome"], _fmt_pct(r["dividend_yield"]), r["setor"]))
    partes.append("")

    partes.append("🏦 MENOR ENDIVIDAMENTO (Dívida Líquida/EBITDA)")
    for r in _consultar(cur, "divida_liquida_ebitda", "ASC"):
        v = f"{float(r['divida_liquida_ebitda']):.2f}x" if r["divida_liquida_ebitda"] is not None else "—"
        partes.append(_linha(r["ticker"], r["nome"], v, r["setor"]))
    partes.append("")

    partes.append("📈 MAIOR CRESCIMENTO DE RECEITA (CAGR)")
    for r in _consultar(cur, "cagr_receita", "DESC"):
        partes.append(_linha(r["ticker"], r["nome"], _fmt_pct(r["cagr_receita"]), r["setor"]))
    partes.append("")

    partes.append("🚀 MAIOR VALORIZAÇÃO NOS ÚLTIMOS 12 MESES (preço da ação)")
    for r in _consultar(cur, "variacao_12m", "DESC"):
        partes.append(_linha(r["ticker"], r["nome"], _fmt_pct(r["variacao_12m"]), r["setor"]))
    partes.append("")

    partes.append("📉 MAIOR QUEDA NOS ÚLTIMOS 12 MESES (preço da ação)")
    for r in _consultar(cur, "variacao_12m", "ASC"):
        partes.append(_linha(r["ticker"], r["nome"], _fmt_pct(r["variacao_12m"]), r["setor"]))
    partes.append("")

    partes.append("-" * 50)
    partes.append(
        "Este conteúdo tem caráter exclusivamente informativo e educacional, "
        "não constitui recomendação de compra ou venda de valores mobiliários "
        "(CVM Resolução 20/2021). As metodologias de valuation aqui apresentadas "
        "são simplificações e não substituem análise profissional."
    )

    return "\n".join(partes)


def main():
    conn = conectar(cursor_factory=psycopg2.extras.RealDictCursor)
    cur = conn.cursor()

    texto = montar_texto(cur)
    print(texto)

    os.makedirs(config.PASTA_SAIDA, exist_ok=True)
    caminho = os.path.join(config.PASTA_SAIDA, "Destaques_Semana.txt")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(texto)

    cur.close()
    conn.close()
    print(f"\n(também salvo em: {os.path.abspath(caminho)})")


if __name__ == "__main__":
    main()
