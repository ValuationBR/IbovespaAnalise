"""
Texto explicativo de cada indicador e método de valuation: fórmula usada
e como interpretar. Usado para gerar os comentários de célula no Excel
(clique/passe o mouse sobre o cabeçalho para ver a explicação).
"""

EXPLICACOES = {
    "Preço Atual": "Último preço de fechamento coletado da ação.",
    "Valor de Mercado": "Preço da ação × número de ações. Mostra o tamanho da empresa na bolsa.",
    "Setor": "Setor de atuação da empresa, conforme classificação da B3/brapi.",
    "Variação 12m": (
        "Variação percentual do preço nos últimos 12 meses "
        "(preço atual ÷ preço de ~1 ano atrás − 1). Enquanto o histórico "
        "ainda está sendo acumulado, usa a data mais antiga disponível."
    ),
    "P/L": (
        "Preço / Lucro. Fórmula: Valor de Mercado ÷ Lucro Líquido.\n"
        "Quantos anos de lucro atual seriam necessários para 'pagar' a ação. "
        "Mais baixo pode indicar ação mais barata (ou risco maior); "
        "mais alto pode indicar crescimento esperado (ou ação cara)."
    ),
    "P/VP": (
        "Preço / Valor Patrimonial. Fórmula: Valor de Mercado ÷ Patrimônio Líquido.\n"
        "Compara o preço de mercado com o patrimônio contábil da empresa. "
        "Abaixo de 1 pode indicar desconto em relação ao patrimônio."
    ),
    "ROE": (
        "Return on Equity (Retorno sobre o Patrimônio Líquido). "
        "Fórmula: Lucro Líquido ÷ Patrimônio Líquido.\n"
        "Mostra a rentabilidade que a empresa gera com o capital dos "
        "acionistas. Quanto maior, melhor (em geral)."
    ),
    "ROIC": (
        "Return on Invested Capital (Retorno sobre o Capital Investido). "
        "Fórmula: Lucro Líquido ÷ (Patrimônio Líquido + Dívida Líquida).\n"
        "Mede o retorno sobre todo o capital investido na empresa "
        "(próprio + de terceiros). Quanto maior, mais eficiente a empresa."
    ),
    "ROA": (
        "Return on Assets (Retorno sobre os Ativos). "
        "Fórmula: Lucro Líquido ÷ Ativo Total.\n"
        "Mostra a eficiência da empresa em gerar lucro com todos os seus ativos."
    ),
    "Div. Yield": (
        "Dividend Yield. Fórmula: Dividendos pagos nos últimos 12 meses ÷ Preço Atual.\n"
        "Percentual do preço da ação devolvido em dividendos/JCP no ano. "
        "Quanto maior, mais a ação 'paga' via proventos."
    ),
    "Margem Bruta": (
        "Fórmula: Lucro Bruto ÷ Receita Total.\n"
        "Percentual da receita que sobra depois do custo direto do produto/serviço."
    ),
    "Margem Líquida": (
        "Fórmula: Lucro Líquido ÷ Receita Total.\n"
        "Percentual da receita que vira lucro líquido, depois de todas as despesas e impostos."
    ),
    "Margem EBITDA": (
        "Fórmula: EBITDA ÷ Receita Total.\n"
        "Percentual da receita convertido em geração de caixa operacional, "
        "antes de juros, impostos, depreciação e amortização."
    ),
    "Liq. Corrente": (
        "Liquidez Corrente. Fórmula: Ativo Circulante ÷ Passivo Circulante.\n"
        "Capacidade de pagar as dívidas de curto prazo com os bens/direitos "
        "de curto prazo. Acima de 1 costuma ser considerado saudável."
    ),
    "Dív.Líq/EBITDA": (
        "Dívida Líquida / EBITDA. Fórmula: (Dívida Bruta − Caixa) ÷ EBITDA.\n"
        "Quantos anos de geração de caixa (EBITDA) seriam necessários para "
        "quitar a dívida líquida. Quanto menor (ou negativo/caixa líquido), melhor."
    ),
    "EV/EBITDA": (
        "Enterprise Value / EBITDA. Fórmula: (Valor de Mercado + Dívida Líquida) ÷ EBITDA.\n"
        "Múltiplo de valuation que considera também a dívida da empresa "
        "(diferente do P/L). Comparável entre empresas com estruturas de capital diferentes."
    ),
    "EV/Receita": (
        "Enterprise Value / Receita. Fórmula: (Valor de Mercado + Dívida Líquida) ÷ Receita Total.\n"
        "Quantas vezes a receita anual o mercado está pagando pela empresa (dívida incluída)."
    ),
    "Payout": (
        "Fórmula: Total de Dividendos Pagos ÷ Lucro Líquido Total.\n"
        "Percentual do lucro que a empresa distribuiu como dividendos/JCP. "
        "Acima de 100% significa que distribuiu mais do que lucrou no período."
    ),
    "Giro do Ativo": (
        "Fórmula: Receita Total ÷ Ativo Total.\n"
        "Quantas vezes o ativo total 'gira' em receita no ano. Mede a "
        "eficiência da empresa em gerar vendas com seus ativos."
    ),
    "Correl. Carteira": (
        "Correlação estatística entre os retornos diários da ação e os "
        "retornos médios das 40 empresas selecionadas (uma aproximação do "
        "Ibovespa, calculada só com os dados coletados aqui — não é o "
        "índice oficial). Varia de -1 a 1; perto de 1 = anda junto com o "
        "mercado, perto de 0 = pouco relacionada, negativo = anda ao contrário."
    ),
    "Correl. Setor": (
        "Correlação estatística entre os retornos diários da ação e a "
        "média dos retornos das outras empresas selecionadas do mesmo setor. "
        "Mesma escala da correlação com a carteira (-1 a 1)."
    ),
    "Volatilidade Anual": (
        "Desvio padrão dos retornos diários, anualizado (× raiz de 252 "
        "dias úteis). Mede o quanto o preço da ação costuma oscilar — "
        "quanto maior, mais arriscada/volátil a ação tende a ser."
    ),
    "Beta": (
        "Sensibilidade dos retornos da ação em relação à carteira das 40 "
        "selecionadas (proxy do Ibovespa). Beta = 1 significa que a ação "
        "costuma se mover na mesma intensidade que o mercado; acima de 1, "
        "tende a oscilar mais que o mercado; abaixo de 1, tende a ser mais defensiva."
    ),
    "CAGR Receita": (
        "Crescimento Anual Composto da Receita, calculado entre o primeiro "
        "e o último ano disponível na CVM. Fórmula: (Receita final ÷ Receita "
        "inicial) ^ (1 ÷ nº de anos) − 1. Mostra a taxa média de crescimento "
        "anual da receita no período."
    ),
    "Comentário": (
        "Resumo automático gerado a partir dos indicadores acima, destacando "
        "os pontos mais fortes e os pontos de atenção da empresa. Não é uma "
        "recomendação de compra ou venda — é só um apoio para leitura rápida "
        "da tabela."
    ),
    "Alvo Graham": (
        "Fórmula de Graham: preço justo = raiz quadrada de (22,5 × Lucro por "
        "Ação × Valor Patrimonial por Ação). Método clássico de valuation, "
        "adequado para empresas maduras e lucrativas. Fica em branco se o "
        "lucro por ação ou o valor patrimonial por ação forem negativos."
    ),
    "Alvo Bazin": (
        "Método de Bazin: preço-teto = Dividendo pago nos últimos 12 meses "
        "por ação ÷ 6%. Método focado em geração de dividendos — parte da "
        "ideia de que a ação deveria pagar, no preço-teto, pelo menos 6% de "
        "yield ao ano. Fica em branco se a empresa não pagou dividendos no período."
    ),
    "Alvo DCF": (
        "Fluxo de Caixa Descontado simplificado (modelo de perpetuidade de "
        "Gordon): valor da empresa = FCF projetado ÷ (taxa de desconto − "
        "crescimento na perpetuidade); preço-alvo = valor da empresa ÷ nº "
        "de ações. O FCF é aproximado como 75% do EBITDA (proxy simples de "
        "capex e impostos, já que o fluxo de caixa livre exato não está "
        "disponível nas fontes gratuitas usadas)."
    ),
    "Alvo Médio": "Média simples dos preços-alvo calculados pelos métodos disponíveis (Graham, Bazin e DCF).",
    "Upside %": "Diferença percentual entre o preço-alvo médio e o preço atual. Positivo sugere potencial de valorização segundo os métodos usados; negativo sugere que a ação já estaria 'esticada'.",
    "Variação Alvo 12m": (
        "Variação percentual do PRÓPRIO preço-alvo médio (calculado pelos "
        "3 métodos) nos últimos 12 meses — mostra se as estimativas de "
        "valuation desta empresa estão subindo ou caindo ao longo do "
        "tempo, à medida que novos balanços e preços entram na conta. "
        "Diferente da 'Variação 12m', que é sobre o preço de mercado da "
        "ação. Enquanto o histórico ainda está sendo acumulado, usa a "
        "data mais antiga disponível."
    ),
    "Observações (notícias da semana)": (
        "Manchetes recentes (últimos 7 dias) sobre a empresa, encontradas "
        "no Google Notícias, com um comentário automático sobre o possível "
        "impacto (classificação por palavra-chave, ou gerado por IA se "
        "configurado em config.py). Não é uma checagem editorial — sempre "
        "vale ler a notícia completa antes de tirar conclusões."
    ),
}
