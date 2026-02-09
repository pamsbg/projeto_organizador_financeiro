# 💰 Organizador Financeiro Família Guerra Possa

Aplicativo completo de controle financeiro pessoal e familiar desenvolvido em Python com [Streamlit](https://streamlit.io/).

## 🌟 Funcionalidades

### 💰 Gerenciamento de Receitas
- Registre fontes de renda mensais (salários, freelance, rendas extras)
- Controle separado por pessoa (Pamela, Renato, Família)
- Filtragem por mês e ano
- Tipos de renda: Fixo, Variável, Extra
- Recorrência: Mensal, Única, Anual

### 📊 Dashboard Interativo
- **KPIs em tempo real**: Total de gastos, maior categoria, quantidade de compras
- **Tabela detalhada de categorias**: Veja total gasto, número de compras, valor médio e percentual por categoria
- **Gráfico de pizza**: Distribuição visual dos gastos
- **Top 5 locais**: Onde você mais gasta
- **Evolução temporal**: Acompanhe seus gastos dia a dia no mês

### 📥 Importação Inteligente
- Importe faturas de cartão (CSV) e extratos bancários
- Detecção automática de formato (Nubank, Itaú, e outros)
- Extração automática de data do nome do arquivo
- Categorização automática baseada em regras + aprendizado de máquina

### 🧙‍♂️ Mágico de Categorização
- Categorizador inteligente que aprende com suas escolhas
- Sugestões automáticas baseadas em padrões históricos
- Edição em lote de transações
- Salva automaticamente ao aplicar

### 📝 Gerenciamento de Transações
- Editor completo de transações
- Filtros por mês, ano, pessoa e busca por texto
- Ordenação personalizável (data, valor, categoria, descrição)
- Adição manual de transações
- Suporte a parcelamento

### 🎯 Planejamento Financeiro
- Defina metas de gastos por categoria
- Metas personalizadas por mês e pessoa
- Compare gastos reais vs planejado
- Indicadores visuais de progresso

### 🔮 Projeções
- Visualize o fluxo de caixa mensal
- Acompanhe crescimento de patrimônio
- Projeções baseadas em dados reais

### 👥 Multi-Usuário
- Separe transações por pessoa (Pamela, Renato, Família)
- Visão unificada ("Todos") ou individual
- Filtro global aplicável a todas as abas

## 🔒 Sistema de Login
- Acesso protegido por senha
- Configurável via `.streamlit/secrets.toml`
- Proteção de dados financeiros sensíveis

## 📦 Onde os Dados São Salvos?

**Todos os dados são salvos localmente no seu computador**, na pasta do projeto:

- `base_financeira.csv` - Transações e gastos
- `receitas.csv` - Fontes de renda
- `settings.json` - Categorias e metas

**Nada é enviado para a nuvem ou GitHub.** Para mais detalhes, veja [`DATA_PERSISTENCE.md`](DATA_PERSISTENCE.md).

## 🚀 Como Rodar o Projeto

### Pré-requisitos
- Python 3.8+
- Pip

### Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/SEU_USUARIO/projeto_organizador_financeiro.git
   cd projeto_organizador_financeiro
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure a senha de acesso:
   - Crie o arquivo `.streamlit/secrets.toml`
   - Adicione: `password = "sua_senha_aqui"`
   - Veja [`SECRETS_GUIDE.md`](SECRETS_GUIDE.md) para mais detalhes

4. Execute a aplicação:
   ```bash
   streamlit run app.py
   ```

5. Abra o navegador em `http://localhost:8501`

## 📖 Documentação

- [Manual de Uso](manual_de_uso.md) - Como usar cada funcionalidade
- [Guia de Persistência de Dados](DATA_PERSISTENCE.md) - Onde e como os dados são salvos
- [Configuração de Senha](SECRETS_GUIDE.md) - Como configurar o sistema de login

## 🏗️ Estrutura do Projeto

```
projeto_organizador_financeiro/
├── app.py                      # Aplicação principal Streamlit
├── utils.py                    # Funções de I/O e processamento
├── ml_patterns.py              # Aprendizado de máquina para categorização
├── ai_utils.py                 # Integração com Gemini AI
├── base_financeira.csv         # Dados de transações (local, não versionado)
├── receitas.csv                # Dados de receitas (local, não versionado)
├── settings.json               # Configurações (local, não versionado)
├── requirements.txt            # Dependências Python
├── .gitignore                  # Proteção de dados pessoais
├── .streamlit/
│   └── secrets.toml            # Senha e configurações (não versionado)
├── faturas_itau_pamela/        # Faturas importadas (não versionado)
├── faturas_nubank_renato/      # Faturas importadas (não versionado)
└── docs/
    ├── README.md               # Este arquivo
    ├── manual_de_uso.md        # Manual completo
    ├── DATA_PERSISTENCE.md     # Guia de dados
    └── SECRETS_GUIDE.md        # Configuração de senha
```

## 🔧 Tecnologias Utilizadas

- **[Streamlit](https://streamlit.io/)** - Framework de UI
- **[Pandas](https://pandas.pydata.org/)** - Manipulação de dados
- **[Plotly](https://plotly.com/python/)** - Gráficos interativos
- **[Google Generative AI](https://ai.google.dev/)** - Categorização inteligente (opcional)

## 🛡️ Privacidade e Segurança

### ✅ O que NÃO vai pro GitHub:
- Transações financeiras (`*.csv`)
- Receitas (`receitas.csv`)
- Configurações pessoais (`settings.json`)
- Faturas importadas (`faturas_*/`)
- Senhas (`.streamlit/secrets.toml`)

### ✅ O que VAI pro GitHub:
- Código da aplicação
- Documentação
- Dependências

**Seus dados financeiros permanecem 100% no seu computador.**

## 🐛 Bugs Conhecidos Corrigidos

### ✅ Bug de Receitas (Corrigido em 09/02/2026)
- **Problema**: Deletar receita de um mês deletava de todos os meses
- **Solução**: Corrigida lógica de filtros com operadores OR
- **Status**: Resolvido ✅

### ✅ Dashboard Pouco Claro (Melhorado em 09/02/2026)
- **Problema**: Visualização confusa, falta de tabela de categorias
- **Solução**: Adicionada tabela detalhada, reorganizado layout em seções
- **Status**: Melhorado ✅

## 📝 To-Do / Roadmap

- [ ] Exportar relatórios em PDF
- [ ] Gráficos de comparação mensal
- [ ] Alertas de orçamento excedido
- [ ] Importação automática via API bancária
- [ ] App mobile (versão responsiva)
- [ ] Backup automático em nuvem (opcional)

## 🤝 Contribuindo

Este é um projeto privado/familiar, mas sugestões são bem-vindas! Abra uma issue ou pull request.

## 📄 Licença

Projeto de uso pessoal e familiar. Código disponível para aprendizado.

---

**Desenvolvido com ❤️ para a Família Guerra Possa**
