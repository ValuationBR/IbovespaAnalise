"""
Busca, direto na API gratuita do Banco Central do Brasil (SGS - Sistema
Gerenciador de Séries Temporais, sem necessidade de chave), as taxas de
juros mais recentes:
 - Selic Meta (definida pelo Copom) — referência de curto prazo
 - CDI — acompanha de perto a Selic
 - IPCA mensal — inflação do último mês fechado

Documentação: https://dadosabertos.bcb.gov.br

OBSERVAÇÃO HONESTA: o Banco Central não publica uma única série simples
de "taxa de juros de longo prazo" (tipo um título de 10 anos) de forma
tão direta quanto a Selic. Se você quiser uma referência de prazo mais
longo, a alternativa mais usada no mercado é acompanhar as taxas de DI
futuro negociadas na B3 — que não têm uma API gratuita e simples como a
do BCB. Por ora, este módulo cobre o que é possível buscar de forma
confiável e 100% gratuita.
"""
import requests

BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/1?formato=json"

SERIES = {
    "selic_meta": 432,   # Taxa Selic Meta definida pelo Copom (% a.a.)
    "cdi": 12,           # CDI (% a.a.)
    "ipca_mensal": 433,  # IPCA - variação mensal (%)
}


def _buscar_serie(codigo):
    try:
        resp = requests.get(BASE_URL.format(codigo=codigo), timeout=15)
        resp.raise_for_status()
        dados = resp.json()
        if not dados:
            return None, None
        ultimo = dados[-1]
        return ultimo.get("valor"), ultimo.get("data")
    except Exception:
        return None, None


def buscar_taxas():
    """Retorna um dicionário com as taxas mais recentes, ou None onde não
    foi possível buscar (o site continua funcionando normalmente, só não
    mostra aquele valor)."""
    resultado = {}
    for nome, codigo in SERIES.items():
        valor, data = _buscar_serie(codigo)
        resultado[nome] = {"valor": valor, "data": data}
    return resultado


if __name__ == "__main__":
    print(buscar_taxas())
