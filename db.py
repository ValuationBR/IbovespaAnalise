"""
Ponto único de conexão com o banco de dados. Todos os outros scripts
importam a função conectar() daqui, em vez de duplicá-la — assim, trocar
de um PostgreSQL local (pgAdmin4) para um banco na nuvem (ex: Supabase)
é só uma questão de editar config.py, sem mexer em mais nada.
"""
import psycopg2
import config


def conectar(cursor_factory=None):
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        sslmode=getattr(config, "DB_SSLMODE", "prefer"),
        cursor_factory=cursor_factory,
    )
