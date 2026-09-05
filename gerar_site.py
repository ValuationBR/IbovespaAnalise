"""
Gera um site estático (só arquivos .html, sem servidor) a partir dos
mesmos dados usados no Excel: uma página inicial com a tabela das 40
empresas e uma página por empresa com gráfico de preço, indicadores,
valuation, comentário automático e notícias da semana.

O resultado fica na pasta site/ — é só publicar essa pasta em qualquer
hospedagem estática gratuita (Netlify, Vercel, GitHub Pages). Veja o
guia SITE_PASSO_A_PASSO.txt para o passo a passo completo.

Roda separado de atualizar_tudo.py (não faz parte do pipeline automático
por padrão) — rode manualmente, ou adicione como mais uma etapa se quiser
publicar o site todo dia junto com o resto.
"""
import os
import json
import shutil
import html
from datetime import date
from decimal import Decimal

import psycopg2.extras
from jinja2 import Template

from db import conectar
from explicacoes import EXPLICACOES
import config
from taxas_bcb import buscar_taxas

PASTA_SITE = "site"

DISCLAIMER = (
    "Este conteúdo tem caráter exclusivamente informativo e educacional, não "
    "constitui recomendação de compra ou venda de valores mobiliários (CVM "
    "Resolução 20/2021). As metodologias de valuation aqui apresentadas são "
    "simplificações e não substituem análise profissional."
)

CSS_BASE = """
:root {
  --azul-escuro: #1f3864; --azul-claro: #eaf1fb; --verde: #1e7e34;
  --vermelho: #b02a2a; --cinza: #6b7280; --borda: #e5e7eb; --bg: #f7f8fa;
}
* { box-sizing: border-box; }
body { font-family: -apple-system, "Segoe UI", Arial, sans-serif; background: var(--bg);
       color: #1a1a1a; margin: 0; line-height: 1.5; }
header { background: var(--azul-escuro); color: #fff; padding: 24px 20px; }
header h1 { margin: 0; font-size: 1.5rem; }
header p { margin: 4px 0 0; color: #cbd8ef; font-size: 0.9rem; }
main { max-width: 1100px; margin: 0 auto; padding: 24px 16px 60px; }
a { color: var(--azul-escuro); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px; }
.card { background: #fff; border: 1px solid var(--borda); border-radius: 12px; padding: 18px;
        text-decoration: none; color: inherit; display: block; transition: box-shadow .15s, transform .15s; }
.card:hover { box-shadow: 0 6px 16px rgba(31,56,100,.10); transform: translateY(-2px); }
.card .top { display: flex; justify-content: space-between; align-items: baseline; }
.card .ticker { font-weight: 700; font-size: 1.1rem; color: var(--azul-escuro); }
.card .nome, .card .setor { color: var(--cinza); font-size: 0.82rem; margin-top: 2px; }
.card .preco { font-size: 1.35rem; font-weight: 700; margin-top: 10px; color: #1a1a1a; }
.card .linha-mini { display: flex; justify-content: space-between; margin-top: 10px; font-size: 0.82rem; color: var(--cinza); }
.pill { display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 0.78rem; font-weight: 700; }
.pill.pos { background: #e6f4ea; color: var(--verde); }
.pill.neg { background: #fbe9e9; color: var(--vermelho); }
table { border-collapse: collapse; width: 100%; font-size: 0.88rem; background: #fff; }
th, td { padding: 8px 10px; border-bottom: 1px solid var(--borda); text-align: left; white-space: nowrap; }
th { background: var(--azul-claro); color: var(--azul-escuro); position: sticky; top: 0; }
.table-wrap { overflow-x: auto; border: 1px solid var(--borda); border-radius: 8px; }
.secao { margin-top: 28px; }
.secao h2 { color: var(--azul-escuro); font-size: 1.1rem; border-bottom: 2px solid var(--azul-claro); padding-bottom: 6px; }
.indicadores { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
.indicador { background: #fff; border: 1px solid var(--borda); border-radius: 8px; padding: 10px 12px; }
.indicador .label { font-size: 0.75rem; color: var(--cinza); }
.indicador .valor { font-size: 1.05rem; font-weight: 700; }
.noticia { background: #fff; border: 1px solid var(--borda); border-radius: 8px; padding: 12px; margin-bottom: 8px; }
.noticia .data { color: var(--cinza); font-size: 0.78rem; }
.comentario-box { background: #fff; border-left: 4px solid var(--azul-escuro); padding: 12px 16px; border-radius: 6px; }
footer { color: var(--cinza); font-size: 0.78rem; padding: 20px 16px 40px; max-width: 1100px; margin: 0 auto; }
.voltar { display: inline-block; margin-bottom: 16px; font-size: 0.9rem; }
.intro { background: #fff; border: 1px solid var(--borda); border-radius: 12px; padding: 18px 20px; margin-bottom: 20px; }
.intro p { margin: 0 0 8px; color: #374151; font-size: 0.92rem; }
.intro p:last-child { margin-bottom: 0; }
.selo { display: inline-flex; align-items: center; gap: 6px; background: var(--azul-claro); color: var(--azul-escuro);
        font-size: 0.78rem; font-weight: 600; padding: 4px 10px; border-radius: 999px; margin-bottom: 10px; }
.feedback { background: #fff; border: 1px solid var(--borda); border-radius: 12px; padding: 20px; margin-top: 32px; text-align: center; }
.feedback h2 { margin-top: 0; color: var(--azul-escuro); font-size: 1.05rem; }
.feedback p { color: var(--cinza); font-size: 0.88rem; }
.botao { display: inline-block; background: var(--azul-escuro); color: #fff; padding: 10px 20px;
         border-radius: 8px; font-weight: 600; font-size: 0.88rem; margin-top: 6px; }
.taxas-bcb { display: flex; gap: 10px; flex-wrap: wrap; margin: 14px 0 4px; }
.taxa-item { background: var(--azul-claro); border-radius: 8px; padding: 8px 14px; font-size: 0.85rem; }
.taxa-item b { color: var(--azul-escuro); font-size: 1rem; }
.taxa-item .taxa-data { color: var(--cinza); font-size: 0.72rem; display: block; }
.ticker-tape-wrap { border-bottom: 1px solid var(--borda); background: #fff; }
.delay-notice { text-align: center; font-size: 0.74rem; color: var(--cinza); padding: 5px 8px; background: #fff; border-bottom: 1px solid var(--borda); }
.brand { display: flex; align-items: center; gap: 10px; }
.brand-icon svg { display: block; }
.brand-name { font-size: 1.5rem; font-weight: 800; letter-spacing: -0.3px; color: #fff; }
.brand-name b { color: #35d492; font-weight: 800; }
.hero-ibov { background: linear-gradient(135deg, var(--azul-escuro), #2c4d82); color: #fff;
             border-radius: 14px; padding: 18px 20px; margin-bottom: 16px; }
.hero-ibov h3 { margin: 0; font-size: 1rem; font-weight: 700; }
.hero-ibov .hero-sub { color: #cbd8ef; font-size: 0.78rem; margin: 2px 0 8px; }
.destaques { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; margin-bottom: 20px; }
.destaque-item { background: #fff; border: 1px solid var(--borda); border-left: 4px solid var(--azul-escuro);
                  border-radius: 8px; padding: 12px 14px; font-size: 0.85rem; color: #374151; }
.destaque-item .rotulo { display: block; font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
                          letter-spacing: .04em; color: var(--azul-escuro); margin-bottom: 4px; }
.card .logo-linha { display: flex; align-items: center; gap: 8px; }
.card .avatar { width: 28px; height: 28px; border-radius: 50%; background: var(--azul-claro); color: var(--azul-escuro);
                font-size: 0.7rem; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.card .logo-img { width: 28px; height: 28px; border-radius: 50%; object-fit: contain; background: #fff; border: 1px solid var(--borda); flex-shrink: 0; }

/* Tooltip de explicação — funciona com mouse (hover) e toque (clique) */
.tip { position: relative; cursor: help; border-bottom: 1px dotted var(--cinza); }
.tip::after {
  content: attr(data-tip);
  position: absolute; left: 0; bottom: 130%; z-index: 30;
  background: #1a1a1a; color: #fff; padding: 10px 12px; border-radius: 8px;
  font-size: 0.78rem; font-weight: 400; line-height: 1.45;
  width: 260px; max-width: 75vw; box-shadow: 0 8px 22px rgba(0,0,0,.22);
  opacity: 0; visibility: hidden; transform: translateY(4px);
  transition: opacity .12s, transform .12s; pointer-events: none;
}
.tip:hover::after, .tip.show::after { opacity: 1; visibility: visible; transform: translateY(0); }
"""

JS_TOOLTIP = """
document.querySelectorAll('.tip').forEach(function(el) {
  el.addEventListener('click', function(ev) {
    ev.stopPropagation();
    document.querySelectorAll('.tip.show').forEach(function(o) { if (o !== el) o.classList.remove('show'); });
    el.classList.toggle('show');
  });
});
document.addEventListener('click', function() {
  document.querySelectorAll('.tip.show').forEach(function(el) { el.classList.remove('show'); });
});
"""

# Ícone do logo: uma linha ascendente (tendência de alta), usado no cabeçalho e como favicon
LOGO_ICON_SVG = (
    '<svg width="32" height="32" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M4 30 L14 18 L20 24 L36 8" stroke="#35d492" stroke-width="4.5" fill="none" '
    'stroke-linecap="round" stroke-linejoin="round"/>'
    '<circle cx="36" cy="8" r="3.4" fill="#35d492"/></svg>'
)
FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">'
    '<rect width="40" height="40" rx="8" fill="#1f3864"/>'
    '<path d="M6 30 L15 19 L21 25 L34 10" stroke="#35d492" stroke-width="4.5" fill="none" '
    'stroke-linecap="round" stroke-linejoin="round"/>'
    '<circle cx="34" cy="10" r="3.2" fill="#35d492"/></svg>'
)

TEMPLATE_INDEX = Template("""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ValuationBR — 40 Maiores do Ibovespa por Valor de Mercado</title>
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<style>{{ css }}</style></head>
<body>
<header>
<div class="brand">{{ logo_icon | safe }}<span class="brand-name">Valuation<b>BR</b></span></div>
<p>40 maiores do Ibovespa por valor de mercado · Atualizado em {{ hoje }}</p></header>

<div class="ticker-tape-wrap">
<div class="tradingview-widget-container">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
  {
  "symbols": {{ ticker_tape_symbols | safe }},
  "showSymbolLogo": true,
  "isTransparent": false,
  "displayMode": "adaptive",
  "colorTheme": "light",
  "locale": "br"
  }
  </script>
</div>
</div>
<div class="delay-notice">⏱️ Cotações com defasagem de aproximadamente 15 minutos.</div>

<main>

<div class="intro">
<span class="selo">🔄 Atualização automática diária</span>
<p>Este portal é uma ferramenta que reúne, organiza e calcula indicadores a partir de fontes
públicas e oficiais sobre as empresas do Ibovespa: preços e proventos da B3, e Demonstrações
Financeiras (DRE e Balanço Patrimonial) da CVM. Brevemente outros índices e ações constituintes
estarão disponíveis.</p>
<p>Os dados são coletados e recalculados automaticamente todos os dias com o apoio do Claude.AI.
Toda a informação disponível neste portal pretende ser informativa e não é recomendação de
investimento.</p>
{% if taxas %}
<div class="taxas-bcb">
  {% if taxas.selic_meta.valor %}<div class="taxa-item">Selic Meta: <b>{{ taxas.selic_meta.valor }}% a.a.</b><span class="taxa-data">Banco Central · {{ taxas.selic_meta.data }}</span></div>{% endif %}
  {% if taxas.ipca_mensal.valor %}<div class="taxa-item">IPCA (mês): <b>{{ taxas.ipca_mensal.valor }}%</b><span class="taxa-data">Banco Central · {{ taxas.ipca_mensal.data }}</span></div>{% endif %}
</div>
{% endif %}
</div>

{% if destaques %}
<div class="destaques">
  {% if destaques.semana %}<div class="destaque-item"><span class="rotulo">📌 Destaque da semana</span>{{ destaques.semana }}</div>{% endif %}
  {% if destaques.alta_dia %}<div class="destaque-item"><span class="rotulo">🔼 Destaque do dia</span>{{ destaques.alta_dia }}</div>{% endif %}
  {% if destaques.queda_dia %}<div class="destaque-item"><span class="rotulo">🔽 Destaque do dia</span>{{ destaques.queda_dia }}</div>{% endif %}
</div>
{% endif %}

<div class="hero-ibov">
<h3>📊 Índice Ibovespa</h3>
<div class="hero-sub">Cotação com defasagem de ~15 minutos</div>
<div class="tradingview-widget-container">
<div class="tradingview-widget-container__widget"></div>
<script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js" async>
{
"symbol": "BMFBOVESPA:IBOV",
"width": "100%",
"height": "150",
"locale": "br",
"dateRange": "1D",
"colorTheme": "dark",
"trendLineColor": "rgba(53, 212, 146, 1)",
"underLineColor": "rgba(53, 212, 146, 0.15)",
"isTransparent": true,
"autosize": true
}
</script>
</div>
</div>

<div class="grid">
{% for e in empresas %}
<a class="card" href="{{ e.ticker }}.html">
<div class="top">
<div class="logo-linha">
{% if e.logo_url %}<img class="logo-img" src="{{ e.logo_url }}" alt="{{ e.ticker }}" loading="lazy">{% else %}<div class="avatar">{{ e.ticker[:2] }}</div>{% endif %}
<div class="ticker">{{ e.ticker }}</div>
</div>
<span class="pill {{ 'pos' if e.var_dia_pos else 'neg' }}">{{ e.var_dia_fmt }}</span></div>
<div class="setor">{{ e.nome }} · {{ e.setor or '—' }}</div>
<div class="preco">{{ e.preco_fmt }}</div>
<div class="linha-mini"><span>P/L {{ e.pl_fmt }}</span><span>DY {{ e.dy_fmt }}</span><span>12m {{ e.var12m_fmt }}</span></div>
</a>
{% endfor %}
</div>

<div class="feedback">
<h2>O que você achou do portal?</h2>
<p>Sua opinião ajuda a decidir o que melhorar primeiro — leva menos de 1 minuto.</p>
<a class="botao" href="{{ link_feedback }}" target="_blank" rel="noopener">Deixar minha avaliação</a>
</div>

</main>
<footer>{{ disclaimer }}</footer>
</body></html>""")

TEMPLATE_EMPRESA = Template("""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ e.ticker }} — {{ e.nome }} · ValuationBR</title>
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<style>{{ css }}</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
</head>
<body>
<header>
<div class="brand">{{ logo_icon | safe }}<span class="brand-name">Valuation<b>BR</b></span></div>
<p>{{ e.ticker }} — {{ e.nome }} · {{ e.setor or '' }} · Atualizado em {{ hoje }}</p></header>
<main>
<a class="voltar" href="index.html">&larr; Voltar para todas as empresas</a>

<h1 style="color:var(--azul-escuro); font-size:1.4rem; margin: 0 0 12px;">{{ e.ticker }} — {{ e.nome }}</h1>

<div class="intro">
<p>Aqui poderão verificar todos os dados relevantes para uma análise fundamental da ação.
O Claude.AI nos auxilia com a coleta de notícias relevantes diariamente, classificando o
potencial peso das mesmas no valuation da ação e avalia os pontos fortes e fracos da ação.</p>
</div>

<div class="secao">
<h2>Evolução do preço</h2>
<canvas id="grafico" height="90"></canvas>
</div>

<div class="secao">
<h2>Indicadores <span style="font-weight:400;font-size:0.75rem;color:var(--cinza)">(passe o mouse ou clique no nome)</span></h2>
<div class="indicadores">
{% for label, valor, tip in e.indicadores %}
<div class="indicador"><div class="label {{ 'tip' if tip }}" data-tip="{{ tip }}">{{ label }}</div><div class="valor">{{ valor }}</div></div>
{% endfor %}
</div>
</div>

<div class="secao">
<h2>Valuation — preço-alvo por método</h2>
<div class="table-wrap"><table>
<tr><th>Método</th><th>Preço-alvo</th><th>Upside</th></tr>
{% for nome, preco, upside, tip in e.valuation %}
<tr><td class="{{ 'tip' if tip }}" data-tip="{{ tip }}">{{ nome }}</td><td>{{ preco }}</td><td>{{ upside }}</td></tr>
{% endfor %}
</table></div>
</div>

<div class="secao">
<h2>Comentário automático</h2>
<div class="comentario-box">{{ e.comentario or 'Sem comentário disponível.' }}</div>
</div>

<div class="secao">
<h2>Notícias recentes</h2>
{% if e.noticias %}
{% for n in e.noticias %}
<div class="noticia"><div class="data">{{ n.data }} — {{ n.fonte }}</div>
<strong>{{ n.titulo }}</strong><br>{{ n.comentario }}</div>
{% endfor %}
{% else %}
<p>Nenhuma notícia relevante coletada na última semana.</p>
{% endif %}
</div>

</main>
<footer>{{ disclaimer }}</footer>
<script>
const dados = {{ precos_json | safe }};
new Chart(document.getElementById('grafico'), {
  type: 'line',
  data: { labels: dados.map(p => p.d), datasets: [{ label: 'Preço (R$)', data: dados.map(p => p.v),
    borderColor: '#1f3864', backgroundColor: 'rgba(31,56,100,0.08)', fill: true, tension: 0.15, pointRadius: 0 }] },
  options: { responsive: true, plugins: { legend: { display: false } },
    scales: { x: { ticks: { maxTicksLimit: 8 } } } }
});
</script>
<script>{{ js_tooltip }}</script>
</body></html>""")


def _fmt_moeda(v):
    return f"R$ {float(v):.2f}" if v is not None else "—"


def _tip(label):
    texto = EXPLICACOES.get(label)
    if not texto:
        return ""
    return html.escape(texto.replace("\n", " "))


def _fmt_pct(v):
    return f"{float(v) * 100:.1f}%" if v is not None else "—"


def _fmt_x(v):
    return f"{float(v):.2f}x" if v is not None else "—"


def _fmt_num(v):
    return f"{float(v):.2f}" if v is not None else "—"


def _num(v):
    return float(v) if isinstance(v, Decimal) else v


def montar_empresas_resumo(cur):
    cur.execute(
        """SELECT e.ticker, e.nome, e.setor, e.logo_url, i.preco_atual, i.variacao_12m,
                  i.variacao_diaria, i.pl, i.pvp, i.dividend_yield,
                  v.preco_alvo_medio, v.upside_medio_pct
           FROM empresas e
           LEFT JOIN indicadores i ON i.ticker = e.ticker
           LEFT JOIN valuation v ON v.ticker = e.ticker
           WHERE e.selecionada = TRUE
           ORDER BY i.market_cap DESC NULLS LAST"""
    )
    empresas = []
    for r in cur.fetchall():
        var_dia = _num(r["variacao_diaria"])
        empresas.append({
            "ticker": r["ticker"], "nome": r["nome"], "setor": r["setor"],
            "logo_url": r["logo_url"],
            "preco_fmt": _fmt_moeda(r["preco_atual"]),
            "var12m_fmt": _fmt_pct(r["variacao_12m"]),
            "var_dia_fmt": _fmt_pct(r["variacao_diaria"]),
            "var_dia_pos": (var_dia or 0) >= 0,
            "var_dia_raw": var_dia,
            "pl_fmt": _fmt_x(r["pl"]), "pvp_fmt": _fmt_x(r["pvp"]),
            "dy_fmt": _fmt_pct(r["dividend_yield"]),
            "alvo_fmt": _fmt_moeda(r["preco_alvo_medio"]),
            "upside_fmt": _fmt_pct(r["upside_medio_pct"]),
            "upside_raw": _num(r["upside_medio_pct"]),
        })
    return empresas


def montar_destaques(empresas_resumo):
    """Textos curtos de destaque (semana + dia), gerados a partir dos
    próprios dados calculados — usados na página inicial."""
    textos = {}

    validos_upside = [e for e in empresas_resumo if e["upside_raw"] is not None]
    if validos_upside:
        d = max(validos_upside, key=lambda e: e["upside_raw"])
        textos["semana"] = (
            f"{d['ticker']} ({d['nome']}) aparece com o maior potencial estimado pela média dos "
            f"3 métodos de valuation: upside de {d['upside_fmt']} sobre o preço atual ({d['preco_fmt']})."
        )

    validos_dia = [e for e in empresas_resumo if e["var_dia_raw"] is not None]
    if validos_dia:
        ordenados = sorted(validos_dia, key=lambda e: e["var_dia_raw"], reverse=True)
        maior_alta = ordenados[0]
        maior_queda = ordenados[-1]
        if maior_alta["var_dia_raw"] > 0:
            textos["alta_dia"] = (
                f"{maior_alta['ticker']} ({maior_alta['nome']}) lidera as altas do dia, "
                f"com variação de {maior_alta['var_dia_fmt']}."
            )
        if maior_queda is not maior_alta and maior_queda["var_dia_raw"] < 0:
            textos["queda_dia"] = (
                f"{maior_queda['ticker']} ({maior_queda['nome']}) teve a maior queda do dia, "
                f"com variação de {maior_queda['var_dia_fmt']}."
            )

    return textos


def montar_pagina_empresa(cur, ticker, nome, setor):
    cur.execute(
        "SELECT data_pregao, preco_fechamento FROM precos_diarios WHERE ticker=%s ORDER BY data_pregao",
        (ticker,),
    )
    precos = [{"d": p["data_pregao"].strftime("%d/%m"), "v": float(p["preco_fechamento"])}
              for p in cur.fetchall() if p["preco_fechamento"]]

    cur.execute("SELECT * FROM indicadores WHERE ticker=%s", (ticker,))
    ind = cur.fetchone() or {}
    lista_ind = [
        ("P/L", _fmt_x(ind.get("pl")), _tip("P/L")), ("P/VP", _fmt_x(ind.get("pvp")), _tip("P/VP")),
        ("ROE", _fmt_pct(ind.get("roe")), _tip("ROE")), ("ROIC", _fmt_pct(ind.get("roic")), _tip("ROIC")),
        ("ROA", _fmt_pct(ind.get("roa")), _tip("ROA")), ("Div. Yield", _fmt_pct(ind.get("dividend_yield")), _tip("Div. Yield")),
        ("Margem Bruta", _fmt_pct(ind.get("margem_bruta")), _tip("Margem Bruta")),
        ("Margem Líquida", _fmt_pct(ind.get("margem_liquida")), _tip("Margem Líquida")),
        ("Margem EBITDA", _fmt_pct(ind.get("margem_ebitda")), _tip("Margem EBITDA")),
        ("Liq. Corrente", _fmt_num(ind.get("liquidez_corrente")), _tip("Liq. Corrente")),
        ("Dív.Líq/EBITDA", _fmt_x(ind.get("divida_liquida_ebitda")), _tip("Dív.Líq/EBITDA")),
        ("EV/EBITDA", _fmt_x(ind.get("ev_ebitda")), _tip("EV/EBITDA")),
        ("EV/Receita", _fmt_x(ind.get("ev_receita")), _tip("EV/Receita")),
        ("Payout", _fmt_pct(ind.get("payout")), _tip("Payout")),
        ("Giro do Ativo", _fmt_num(ind.get("giro_ativo")), _tip("Giro do Ativo")),
        ("Variação 12m", _fmt_pct(ind.get("variacao_12m")), _tip("Variação 12m")),
        ("Correl. Carteira", _fmt_num(ind.get("correlacao_carteira")), _tip("Correl. Carteira")),
        ("Correl. Setor", _fmt_num(ind.get("correlacao_setor")), _tip("Correl. Setor")),
        ("Volatilidade Anual", _fmt_pct(ind.get("volatilidade_anual")), _tip("Volatilidade Anual")),
        ("Beta", _fmt_num(ind.get("beta")), _tip("Beta")),
        ("CAGR Receita", _fmt_pct(ind.get("cagr_receita")), _tip("CAGR Receita")),
    ]

    cur.execute("SELECT * FROM valuation WHERE ticker=%s", (ticker,))
    val = cur.fetchone() or {}
    preco_atual = _num(val.get("preco_atual"))
    metodos = []
    for nome_m, campo in [("Alvo Graham", "preco_alvo_graham"), ("Alvo Bazin", "preco_alvo_bazin"),
                           ("Alvo DCF", "preco_alvo_dcf"), ("Alvo Médio", "preco_alvo_medio")]:
        preco = _num(val.get(campo))
        upside = _fmt_pct((preco / preco_atual - 1)) if (preco and preco_atual) else "—"
        metodos.append((nome_m, _fmt_moeda(preco), upside, _tip(nome_m)))

    cur.execute(
        """SELECT titulo, fonte, data_publicacao, comentario_impacto FROM noticias
           WHERE ticker=%s ORDER BY data_publicacao DESC NULLS LAST LIMIT 5""",
        (ticker,),
    )
    noticias = [{
        "titulo": n["titulo"], "fonte": n["fonte"] or "—",
        "data": n["data_publicacao"].strftime("%d/%m/%Y") if n["data_publicacao"] else "—",
        "comentario": n["comentario_impacto"],
    } for n in cur.fetchall()]

    return {
        "ticker": ticker, "nome": nome, "setor": setor,
        "indicadores": lista_ind, "valuation": metodos,
        "comentario": ind.get("comentario"), "noticias": noticias,
    }, precos


SIMBOLOS_MACRO = [
    {"proName": "BMFBOVESPA:IBOV", "title": "Ibovespa"},
    {"proName": "FX_IDC:USDBRL", "title": "Dólar"},
    {"proName": "FX_IDC:EURBRL", "title": "Euro"},
    {"proName": "FOREXCOM:SPXUSD", "title": "S&P 500"},
    {"proName": "FOREXCOM:NSXUSD", "title": "Nasdaq"},
    {"proName": "FOREXCOM:DJI", "title": "Dow Jones"},
]


def montar_simbolos_ticker_tape(empresas_resumo):
    simbolos_acoes = [{"proName": f"BMFBOVESPA:{e['ticker']}", "title": e["ticker"]} for e in empresas_resumo]
    return SIMBOLOS_MACRO + simbolos_acoes


def main():
    if os.path.isdir(PASTA_SITE):
        shutil.rmtree(PASTA_SITE)
    os.makedirs(PASTA_SITE)

    with open(os.path.join(PASTA_SITE, "favicon.svg"), "w", encoding="utf-8") as f:
        f.write(FAVICON_SVG)

    conn = conectar(cursor_factory=psycopg2.extras.RealDictCursor)
    cur = conn.cursor()

    hoje = date.today().strftime("%d/%m/%Y")

    print("Buscando taxas de juros no Banco Central...")
    taxas = buscar_taxas()

    empresas_resumo = montar_empresas_resumo(cur)
    destaques = montar_destaques(empresas_resumo)
    ticker_tape_symbols = json.dumps(montar_simbolos_ticker_tape(empresas_resumo), ensure_ascii=False)
    html_index = TEMPLATE_INDEX.render(
        empresas=empresas_resumo, hoje=hoje, css=CSS_BASE, disclaimer=DISCLAIMER,
        link_feedback=getattr(config, "LINK_FEEDBACK", "mailto:"),
        taxas=taxas, ticker_tape_symbols=ticker_tape_symbols,
        logo_icon=LOGO_ICON_SVG, destaques=destaques,
    )
    with open(os.path.join(PASTA_SITE, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_index)

    cur.execute("SELECT ticker, nome, setor FROM empresas WHERE selecionada = TRUE ORDER BY ticker")
    empresas = cur.fetchall()
    for emp in empresas:
        dados_pagina, precos = montar_pagina_empresa(cur, emp["ticker"], emp["nome"], emp["setor"])
        html_empresa = TEMPLATE_EMPRESA.render(
            e=dados_pagina, hoje=hoje, css=CSS_BASE, disclaimer=DISCLAIMER,
            precos_json=json.dumps(precos, ensure_ascii=False), js_tooltip=JS_TOOLTIP,
            logo_icon=LOGO_ICON_SVG,
        )
        with open(os.path.join(PASTA_SITE, f"{emp['ticker']}.html"), "w", encoding="utf-8") as f:
            f.write(html_empresa)

    cur.close()
    conn.close()
    print(f"Site gerado em: {os.path.abspath(PASTA_SITE)} ({len(empresas)} páginas de empresa + index.html)")


if __name__ == "__main__":
    main()
