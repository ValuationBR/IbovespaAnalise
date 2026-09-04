"""
Coleta, para cada empresa selecionada, as notícias mais recentes que
saíram na imprensa, usando o RSS gratuito do Google Notícias (não exige
cadastro nem chave de API).

Para cada notícia, gera um comentário curto sobre o possível impacto:
 - Por padrão: uma classificação automática por palavras-chave (100% grátis,
   mas simples — só sinaliza "pode ser positivo/negativo/estratégico" com
   base em termos comuns na notícia).
 - Se você configurar ANTHROPIC_API_KEY em config.py: um comentário mais
   elaborado, gerado por IA (tem custo, veja config.py).

Só olha notícias dos últimos 7 dias, para manter a coluna sempre "fresca".
"""
import time
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote
import xml.etree.ElementTree as ET

import requests
from db import conectar

import config

RSS_URL = "https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-BR"
DIAS_JANELA = 7
MAX_NOTICIAS_POR_EMPRESA = 5
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PainelIbovespa/1.0)"}

PALAVRAS_NEGATIVAS = [
    "queda", "prejuízo", "multa", "investigação", "processo", "greve",
    "paralisação", "recall", "rebaixamento", "downgrade", "demissão",
    "corte de", "escândalo", "fraude", "vazamento", "acidente", "crise",
]
PALAVRAS_POSITIVAS = [
    "recorde", "lucro", "alta de", "aprovação", "aprovado", "crescimento",
    "expansão", "recompra", "dividendo extraordinário", "upgrade", "disparam",
]
PALAVRAS_ESTRATEGICAS = [
    "fusão", "aquisição", "venda de ativo", "parceria", "joint venture",
    "ipo", "follow-on", "cisão", "reestruturação",
]


def _classificar_por_palavra_chave(titulo):
    t = titulo.lower()
    if any(p in t for p in PALAVRAS_NEGATIVAS):
        return "⚠️ Possível impacto negativo (classificação automática por palavra-chave) — vale ler a notícia completa antes de qualquer conclusão."
    if any(p in t for p in PALAVRAS_ESTRATEGICAS):
        return "🔄 Movimento estratégico (fusão/aquisição/parceria) — pode afetar o valuation da empresa."
    if any(p in t for p in PALAVRAS_POSITIVAS):
        return "✅ Possível impacto positivo (classificação automática por palavra-chave)."
    return "ℹ️ Notícia relevante para a empresa, sem classificação automática clara de impacto."


def _gerar_comentario_ia(ticker, nome, titulo):
    if not getattr(config, "ANTHROPIC_API_KEY", ""):
        return None
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": config.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 120,
                "messages": [{
                    "role": "user",
                    "content": (
                        f"Em até 2 frases, em português do Brasil, comente o possível "
                        f"impacto desta notícia para a empresa {nome} ({ticker}). Seja "
                        f"objetivo e cauteloso, não dê recomendação de compra/venda. "
                        f"Notícia: \"{titulo}\""
                    ),
                }],
            },
            timeout=30,
        )
        resp.raise_for_status()
        blocos = resp.json().get("content", [])
        texto = " ".join(b.get("text", "") for b in blocos if b.get("type") == "text").strip()
        return texto or None
    except Exception:
        return None


def buscar_noticias(query):
    url = RSS_URL.format(query=quote(query))
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    raiz = ET.fromstring(resp.content)
    itens = []
    limite = datetime.now(timezone.utc) - timedelta(days=DIAS_JANELA)
    for item in raiz.findall(".//item"):
        titulo = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        fonte_el = item.find("source")
        fonte = fonte_el.text if fonte_el is not None else ""
        data_txt = item.findtext("pubDate")
        try:
            data_pub = parsedate_to_datetime(data_txt) if data_txt else None
        except (TypeError, ValueError):
            data_pub = None
        if data_pub and data_pub < limite:
            continue
        if not titulo:
            continue
        itens.append({"titulo": titulo, "link": link, "fonte": fonte, "data_pub": data_pub})
        if len(itens) >= MAX_NOTICIAS_POR_EMPRESA:
            break
    return itens


def main():
    conn = conectar()
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("SELECT ticker, nome FROM empresas WHERE selecionada = TRUE ORDER BY ticker")
    empresas = cur.fetchall()

    total = len(empresas)
    for i, (ticker, nome) in enumerate(empresas, start=1):
        print(f"[{i}/{total}] Buscando notícias de {ticker} - {nome}...")
        try:
            # remove sufixos tipo "S.A.", "S/A" do nome para melhorar a busca
            nome_busca = re.sub(r"\s+S\.?/?A\.?$", "", nome, flags=re.IGNORECASE).strip()
            query = f'"{nome_busca}" AND (ação OR bolsa OR B3 OR {ticker})'
            itens = buscar_noticias(query)

            for item in itens:
                comentario = _gerar_comentario_ia(ticker, nome, item["titulo"]) or _classificar_por_palavra_chave(item["titulo"])
                data_pub = item["data_pub"].date() if item["data_pub"] else None
                cur.execute(
                    """INSERT INTO noticias (ticker, titulo, fonte, data_publicacao, link, comentario_impacto)
                       VALUES (%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (ticker, titulo) DO UPDATE SET
                          comentario_impacto = EXCLUDED.comentario_impacto,
                          coletado_em = NOW()""",
                    (ticker, item["titulo"], item["fonte"], data_pub, item["link"], comentario),
                )

            cur.execute(
                "INSERT INTO log_execucao (etapa, ticker, status, mensagem) VALUES (%s,%s,%s,%s)",
                ("noticias", ticker, "OK", f"{len(itens)} notícias"),
            )
        except Exception as e:
            print(f"   -> ERRO em {ticker}: {e}")
            cur.execute(
                "INSERT INTO log_execucao (etapa, ticker, status, mensagem) VALUES (%s,%s,%s,%s)",
                ("noticias", ticker, "ERRO", str(e)[:500]),
            )
        time.sleep(1.0)

    # limpa notícias muito antigas (mais de 30 dias), para a tabela não crescer sem limite
    cur.execute("DELETE FROM noticias WHERE data_publicacao < (CURRENT_DATE - INTERVAL '30 days')")

    cur.close()
    conn.close()
    print("Coleta de notícias finalizada.")


if __name__ == "__main__":
    main()
