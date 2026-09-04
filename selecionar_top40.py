"""
Depois de coletar_dados.py trazer o valor de mercado (market_cap) de todas
as empresas do Ibovespa, este script marca as 40 maiores como
"selecionada" no banco. Todos os passos seguintes (dividendos, CVM,
indicadores, valuation, Excel) processam só essas 40 — o que também deixa
o programa bem mais rápido.

A lista das 40 maiores é recalculada a cada execução, então ela sempre
reflete o ranking mais atual (uma empresa pode entrar ou sair do grupo
com o tempo).
"""
from db import conectar
import config

QUANTIDADE_TOP = 40


def main():
    conn = conectar()
    conn.autocommit = True
    cur = conn.cursor()

    # zera a seleção anterior
    cur.execute("UPDATE empresas SET selecionada = FALSE")

    # marca as N maiores por valor de mercado
    cur.execute(
        """UPDATE empresas SET selecionada = TRUE
           WHERE ticker IN (
               SELECT i.ticker FROM indicadores i
               WHERE i.market_cap IS NOT NULL
               ORDER BY i.market_cap DESC
               LIMIT %s
           )""",
        (QUANTIDADE_TOP,),
    )

    cur.execute("SELECT COUNT(*) FROM empresas WHERE selecionada = TRUE")
    total = cur.fetchone()[0]

    cur.execute(
        "SELECT ticker FROM empresas WHERE selecionada = TRUE ORDER BY ticker"
    )
    tickers = [r[0] for r in cur.fetchall()]

    cur.close()
    conn.close()

    print(f"{total} empresas selecionadas (as maiores por valor de mercado): {', '.join(tickers)}")
    if total < QUANTIDADE_TOP:
        print(
            f"AVISO: só foi possível selecionar {total} de {QUANTIDADE_TOP} — "
            "algumas empresas ainda não têm market_cap coletado (rode coletar_dados.py primeiro)."
        )


if __name__ == "__main__":
    main()
