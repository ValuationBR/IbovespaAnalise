-- ============================================================
-- ESTRUTURA DO BANCO DE DADOS - Ibovespa DRE / Balanço / Valuation
-- Este script é executado automaticamente pelo criar_banco.py
-- Não precisa rodar manualmente, mas pode abrir no pgAdmin4 se quiser conferir.
-- ============================================================

CREATE TABLE IF NOT EXISTS empresas (
    ticker          VARCHAR(10) PRIMARY KEY,
    nome            VARCHAR(100) NOT NULL,
    cnpj            VARCHAR(20),
    setor           VARCHAR(100),
    logo_url        TEXT,
    selecionada     BOOLEAN DEFAULT FALSE
);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS logo_url TEXT;
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS cnpj VARCHAR(20);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS setor VARCHAR(100);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS selecionada BOOLEAN DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS precos_diarios (
    id              SERIAL PRIMARY KEY,
    ticker          VARCHAR(10) REFERENCES empresas(ticker),
    data_pregao     DATE NOT NULL,
    preco_fechamento NUMERIC(14,4),
    UNIQUE(ticker, data_pregao)
);

CREATE TABLE IF NOT EXISTS dividendos (
    id              SERIAL PRIMARY KEY,
    ticker          VARCHAR(10) REFERENCES empresas(ticker),
    tipo            VARCHAR(30),          -- DIVIDENDO, JCP, etc.
    valor           NUMERIC(14,6),
    data_pagamento  DATE,
    data_com        DATE,
    UNIQUE(ticker, tipo, valor, data_pagamento)
);

CREATE TABLE IF NOT EXISTS dre_anual (
    id                  SERIAL PRIMARY KEY,
    ticker              VARCHAR(10) REFERENCES empresas(ticker),
    ano_fiscal          INT NOT NULL,
    receita_total       NUMERIC(20,2),
    lucro_bruto         NUMERIC(20,2),
    ebitda              NUMERIC(20,2),
    lucro_liquido       NUMERIC(20,2),
    atualizado_em       TIMESTAMP DEFAULT NOW(),
    UNIQUE(ticker, ano_fiscal)
);

CREATE TABLE IF NOT EXISTS balanco_anual (
    id                      SERIAL PRIMARY KEY,
    ticker                  VARCHAR(10) REFERENCES empresas(ticker),
    ano_fiscal              INT NOT NULL,
    ativo_total             NUMERIC(20,2),
    passivo_total           NUMERIC(20,2),
    patrimonio_liquido      NUMERIC(20,2),
    divida_liquida          NUMERIC(20,2),
    ativo_circulante        NUMERIC(20,2),
    passivo_circulante      NUMERIC(20,2),
    atualizado_em           TIMESTAMP DEFAULT NOW(),
    UNIQUE(ticker, ano_fiscal)
);

CREATE TABLE IF NOT EXISTS indicadores (
    id                      SERIAL PRIMARY KEY,
    ticker                  VARCHAR(10) REFERENCES empresas(ticker) UNIQUE,
    preco_atual             NUMERIC(14,4),
    market_cap              NUMERIC(20,2),
    pl                      NUMERIC(14,4),
    pvp                     NUMERIC(14,4),
    roe                     NUMERIC(14,4),
    roic                    NUMERIC(14,4),
    roa                     NUMERIC(14,4),
    dividend_yield          NUMERIC(14,4),
    margem_bruta            NUMERIC(14,4),
    margem_liquida          NUMERIC(14,4),
    margem_ebitda           NUMERIC(14,4),
    liquidez_corrente       NUMERIC(14,4),
    divida_liquida_ebitda   NUMERIC(14,4),
    ev_ebitda               NUMERIC(14,4),
    ev_receita              NUMERIC(14,4),
    payout                  NUMERIC(14,4),
    giro_ativo              NUMERIC(14,4),
    variacao_12m            NUMERIC(14,4),
    variacao_diaria         NUMERIC(14,4),
    correlacao_carteira     NUMERIC(14,4),
    correlacao_setor        NUMERIC(14,4),
    volatilidade_anual      NUMERIC(14,4),
    beta                    NUMERIC(14,4),
    cagr_receita            NUMERIC(14,4),
    comentario              TEXT,
    atualizado_em           TIMESTAMP DEFAULT NOW()
);
ALTER TABLE indicadores ADD COLUMN IF NOT EXISTS market_cap NUMERIC(20,2);
ALTER TABLE indicadores ADD COLUMN IF NOT EXISTS variacao_12m NUMERIC(14,4);
ALTER TABLE indicadores ADD COLUMN IF NOT EXISTS correlacao_carteira NUMERIC(14,4);
ALTER TABLE indicadores ADD COLUMN IF NOT EXISTS correlacao_setor NUMERIC(14,4);
ALTER TABLE indicadores ADD COLUMN IF NOT EXISTS volatilidade_anual NUMERIC(14,4);
ALTER TABLE indicadores ADD COLUMN IF NOT EXISTS beta NUMERIC(14,4);
ALTER TABLE indicadores ADD COLUMN IF NOT EXISTS cagr_receita NUMERIC(14,4);
ALTER TABLE indicadores ADD COLUMN IF NOT EXISTS comentario TEXT;
ALTER TABLE indicadores ADD COLUMN IF NOT EXISTS variacao_diaria NUMERIC(14,4);

-- Histórico diário dos indicadores (um "retrato" por dia, não sobrescreve
-- o anterior) — permite análise temporal (ex: evolução do P/L ou do ROE
-- de uma empresa ao longo dos meses), diferente da tabela "indicadores"
-- acima, que guarda só o valor mais recente de cada uma.
CREATE TABLE IF NOT EXISTS indicadores_historico (
    id                      SERIAL PRIMARY KEY,
    ticker                  VARCHAR(10) REFERENCES empresas(ticker),
    data_calculo            DATE NOT NULL,
    preco_atual             NUMERIC(14,4),
    market_cap              NUMERIC(20,2),
    pl                      NUMERIC(14,4),
    pvp                     NUMERIC(14,4),
    roe                     NUMERIC(14,4),
    roic                    NUMERIC(14,4),
    roa                     NUMERIC(14,4),
    dividend_yield          NUMERIC(14,4),
    margem_liquida          NUMERIC(14,4),
    divida_liquida_ebitda   NUMERIC(14,4),
    ev_ebitda               NUMERIC(14,4),
    beta                    NUMERIC(14,4),
    volatilidade_anual      NUMERIC(14,4),
    UNIQUE(ticker, data_calculo)
);

CREATE TABLE IF NOT EXISTS valuation (
    id                      SERIAL PRIMARY KEY,
    ticker                  VARCHAR(10) REFERENCES empresas(ticker) UNIQUE,
    preco_atual             NUMERIC(14,4),
    preco_alvo_graham       NUMERIC(14,4),
    preco_alvo_bazin        NUMERIC(14,4),
    preco_alvo_dcf          NUMERIC(14,4),
    preco_alvo_medio        NUMERIC(14,4),
    upside_medio_pct        NUMERIC(14,4),
    variacao_alvo_medio_12m NUMERIC(14,4),
    atualizado_em           TIMESTAMP DEFAULT NOW()
);
ALTER TABLE valuation ADD COLUMN IF NOT EXISTS variacao_alvo_medio_12m NUMERIC(14,4);

CREATE TABLE IF NOT EXISTS valuation_historico (
    id                  SERIAL PRIMARY KEY,
    ticker              VARCHAR(10) REFERENCES empresas(ticker),
    data_calculo        DATE NOT NULL,
    preco_alvo_medio    NUMERIC(14,4),
    UNIQUE(ticker, data_calculo)
);

CREATE TABLE IF NOT EXISTS noticias (
    id                  SERIAL PRIMARY KEY,
    ticker              VARCHAR(10) REFERENCES empresas(ticker),
    titulo              TEXT,
    fonte               VARCHAR(150),
    data_publicacao     DATE,
    link                TEXT,
    comentario_impacto  TEXT,
    coletado_em         TIMESTAMP DEFAULT NOW(),
    UNIQUE(ticker, titulo)
);

CREATE TABLE IF NOT EXISTS log_execucao (
    id              SERIAL PRIMARY KEY,
    etapa           VARCHAR(50),
    ticker          VARCHAR(10),
    status          VARCHAR(20),
    mensagem        TEXT,
    executado_em    TIMESTAMP DEFAULT NOW()
);
