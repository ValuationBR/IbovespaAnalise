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

TEMPLATE_INDEX = Template("""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Painel Ibovespa — 40 Maiores por Valor de Mercado</title>
<style>{{ css }}</style></head>
<body>
<header><h1>Painel Ibovespa — 40 Maiores por Valor de Mercado</h1>
<p>Atualizado em {{ hoje }}</p></header>

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

<main>

<div class="intro">
<span class="selo">🔄 Atualização automática diária</span>
<p><strong>Este portal é uma ferramenta de apoio à decisão</strong> — não uma recomendação de
investimento. Ele reúne, organiza e calcula indicadores a partir de fontes públicas e oficiais
sobre as empresas do Ibovespa: preços e proventos da B3, e Demonstrações Financeiras (DRE e
Balanço Patrimonial) da CVM.</p>
<p>Os dados são coletados e recalculados automaticamente todos os dias, sem intervenção manual.
Passe o mouse (ou toque, no celular) sobre qualquer indicador nas páginas de cada empresa para
ver a fórmula usada e como interpretá-lo.</p>
{% if taxas %}
<div class="taxas-bcb">
  {% if taxas.selic_meta.valor %}<div class="taxa-item">Selic Meta: <b>{{ taxas.selic_meta.valor }}% a.a.</b><span class="taxa-data">Banco Central · {{ taxas.selic_meta.data }}</span></div>{% endif %}
  {% if taxas.cdi.valor %}<div class="taxa-item">CDI: <b>{{ taxas.cdi.valor }}% a.a.</b><span class="taxa-data">Banco Central · {{ taxas.cdi.data }}</span></div>{% endif %}
  {% if taxas.ipca_mensal.valor %}<div class="taxa-item">IPCA (mês): <b>{{ taxas.ipca_mensal.valor }}%</b><span class="taxa-data">Banco Central · {{ taxas.ipca_mensal.data }}</span></div>{% endif %}
</div>
{% endif %}
</div>


<div class="grid">
{% for e in empresas %}
<a class="card" href="{{ e.ticker }}.html">
<div class="top"><div class="ticker">{{ e.ticker }}</div>
<span class="pill {{ 'pos' if e.upside_pos else 'neg' }}">{{ e.upside_fmt }}</span></div>
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
<title>{{ e.ticker }} — {{ e.nome }}</title>
<style>{{ css }}</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
</head>
<body>
<header><h1>{{ e.ticker }} — {{ e.nome }}</h1>
<p>{{ e.setor or '' }} · Atualizado em {{ hoje }}</p></header>
<main>
<a class="voltar" href="index.html">&larr; Voltar para todas as empresas</a>

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
        """SELECT e.ticker, e.nome, e.setor, i.preco_atual, i.variacao_12m,
                  i.pl, i.pvp, i.dividend_yield, v.preco_alvo_medio, v.upside_medio_pct
           FROM empresas e
           LEFT JOIN indicadores i ON i.ticker = e.ticker
           LEFT JOIN valuation v ON v.ticker = e.ticker
           WHERE e.selecionada = TRUE
           ORDER BY i.market_cap DESC NULLS LAST"""
    )
    empresas = []
    for r in cur.fetchall():
        upside = _num(r["upside_medio_pct"])
        empresas.append({
            "ticker": r["ticker"], "nome": r["nome"], "setor": r["setor"],
            "preco_fmt": _fmt_moeda(r["preco_atual"]),
            "var12m_fmt": _fmt_pct(r["variacao_12m"]),
            "pl_fmt": _fmt_x(r["pl"]), "pvp_fmt": _fmt_x(r["pvp"]),
            "dy_fmt": _fmt_pct(r["dividend_yield"]),
            "alvo_fmt": _fmt_moeda(r["preco_alvo_medio"]),
            "upside_fmt": _fmt_pct(r["upside_medio_pct"]),
            "upside_pos": (upside or 0) >= 0,
        })
    return empresas


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

    conn = conectar(cursor_factory=psycopg2.extras.RealDictCursor)
    cur = conn.cursor()

    hoje = date.today().strftime("%d/%m/%Y")

    print("Buscando taxas de juros no Banco Central...")
    taxas = buscar_taxas()

    empresas_resumo = montar_empresas_resumo(cur)
    ticker_tape_symbols = json.dumps(montar_simbolos_ticker_tape(empresas_resumo), ensure_ascii=False)
    html_index = TEMPLATE_INDEX.render(
        empresas=empresas_resumo, hoje=hoje, css=CSS_BASE, disclaimer=DISCLAIMER,
        link_feedback=getattr(config, "LINK_FEEDBACK", "mailto:"),
        taxas=taxas, ticker_tape_symbols=ticker_tape_symbols,
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
        )
        with open(os.path.join(PASTA_SITE, f"{emp['ticker']}.html"), "w", encoding="utf-8") as f:
            f.write(html_empresa)

    cur.close()
    conn.close()
    print(f"Site gerado em: {os.path.abspath(PASTA_SITE)} ({len(empresas)} páginas de empresa + index.html)")


if __name__ == "__main__":
    main()
