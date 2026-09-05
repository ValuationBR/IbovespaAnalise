# ============================================================
#  CONFIGURAÇÕES DO PROJETO
#  Edite os valores abaixo com o Bloco de Notas ou o VS Code.
#  Não é preciso mexer em mais nenhum outro arquivo .py
#
#  IMPORTANTE (se for publicar como site): cada valor aqui primeiro tenta
#  ler de uma "variável de ambiente" (os.environ.get) antes de usar o
#  texto fixo abaixo. Isso existe para que, quando o programa rodar na
#  nuvem (GitHub Actions), ele use as senhas guardadas em "Secrets" do
#  GitHub, em vez do texto deste arquivo — assim você pode deixar o
#  código público no GitHub sem expor sua senha. Rodando no seu PC,
#  isso não muda nada: ele simplesmente usa os valores escritos abaixo.
# ============================================================
import os

# ---- Banco de dados PostgreSQL ----
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "ibovespa_db")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "SUA_SENHA_AQUI")
DB_SSLMODE = os.environ.get("DB_SSLMODE", "prefer")  # "prefer" local; "require" no Supabase/nuvem

# ---- Token gratuito da API brapi.dev ----
# Crie sua conta grátis em https://brapi.dev/dashboard e copie o token.
BRAPI_TOKEN = os.environ.get("BRAPI_TOKEN", "SEU_TOKEN_AQUI")

# ---- Pasta onde o Excel final será salvo ----
PASTA_SAIDA = "saida"            # será criada automaticamente ao lado dos scripts

# ---- Parâmetros de valuation (pode ajustar depois, valores padrão de mercado) ----
TAXA_DESCONTO_DCF = 0.12   # WACC aproximado (12% ao ano) usado no fluxo de caixa descontado
CRESCIMENTO_PERPETUO = 0.03  # crescimento na perpetuidade (3% ao ano) usado no DCF
DY_MINIMO_BAZIN = 0.06      # 6% ao ano, referência do Método de Bazin

# ---- (Opcional) Comentário de notícias gerado por IA ----
# Por padrão, o comentário sobre o possível impacto de cada notícia é
# gerado por uma classificação automática de palavras-chave (100% grátis).
# Se quiser um comentário mais elaborado, gerado por IA de verdade, crie uma
# chave em https://console.anthropic.com/settings/keys e cole abaixo.
# ATENÇÃO: isso tem custo (uso pago por requisição, embora bem barato com o
# modelo usado aqui — geralmente poucos centavos por semana). Deixe em
# branco para continuar usando só a classificação automática gratuita.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ---- (Site) Link de feedback dos visitantes ----
# Por padrão, um link "mailto:" simples (abre o programa de email do
# visitante). Para algo mais estruturado e gratuito, crie um Google Forms
# em https://forms.google.com (grátis, sem necessidade de programar) com
# perguntas tipo "nota de 1 a 5" e "o que você gostaria de ver aqui" — e
# cole o link do formulário abaixo.
LINK_FEEDBACK = os.environ.get("LINK_FEEDBACK", "mailto:seuemail@exemplo.com?subject=Feedback%20Painel%20Ibovespa")
