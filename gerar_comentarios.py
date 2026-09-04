"""
Roda depois de calcular_indicadores.py e valuation.py: gera o comentário
automático de cada empresa selecionada (destacando indicadores fortes e
pontos de atenção) e grava na coluna indicadores.comentario.
"""
import psycopg2.extras
from db import conectar
import config
from comentarios import gerar_comentario


def main():
    conn = conectar()
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT ticker, setor FROM empresas WHERE selecionada = TRUE ORDER BY ticker")
    empresas = cur.fetchall()

    for emp in empresas:
        ticker = emp["ticker"]
        cur.execute("SELECT * FROM indicadores WHERE ticker=%s", (ticker,))
        ind = cur.fetchone() or {}
        cur.execute("SELECT * FROM valuation WHERE ticker=%s", (ticker,))
        val = cur.fetchone() or {}

        comentario = gerar_comentario(ind, val, emp["setor"])

        cur.execute("UPDATE indicadores SET comentario=%s WHERE ticker=%s", (comentario, ticker))

    cur.close()
    conn.close()
    print("Comentários automáticos gerados para as empresas selecionadas.")


if __name__ == "__main__":
    main()
