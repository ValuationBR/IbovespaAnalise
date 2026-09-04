"""
Roda UMA VEZ para criar as tabelas dentro do banco de dados.
Antes de rodar: crie o banco "ibovespa_db" (ou o nome que você
escolheu em config.py) usando o pgAdmin4. Este script só cria
as TABELAS dentro dele, não cria o banco em si.
"""
from db import conectar
import config
from lista_empresas import EMPRESAS_IBOVESPA


def main():
    print("Conectando ao banco de dados...")
    conn = conectar()
    conn.autocommit = True
    cur = conn.cursor()

    print("Criando tabelas (sql/schema.sql)...")
    with open("sql/schema.sql", "r", encoding="utf-8") as f:
        cur.execute(f.read())

    print("Inserindo lista de empresas do Ibovespa...")
    for ticker, nome in EMPRESAS_IBOVESPA:
        cur.execute(
            """INSERT INTO empresas (ticker, nome) VALUES (%s, %s)
               ON CONFLICT (ticker) DO UPDATE SET nome = EXCLUDED.nome""",
            (ticker, nome),
        )

    cur.close()
    conn.close()
    print("Banco de dados pronto! Tabelas e empresas cadastradas com sucesso.")


if __name__ == "__main__":
    main()
