# 📘 Manual de Uso - Organizador Financeiro

Bem-vindo ao **Organizador Financeiro Família Guerra Possa**! Este documento explica como rodar o sistema e como aproveitar cada funcionalidade.

## 🚀 Como Rodar o Sistema Localmente

Para iniciar o aplicativo no seu computador, abra o terminal na pasta do projeto e execute o seguinte comando:

```bash
streamlit run app.py
```

O navegador abrirá automaticamente com o sistema pronto para uso.

---

## 🛠️ Funcionalidades e Abas

### 1. 💰 Receitas (Aba 1)
Aqui você cadastra as **Rendas Mensais** da família.
- **Filtros**: Filtre por mês/ano e pessoa para ver receitas específicas
- **Fonte**: Informe a origem (Salário, Freelance, Bônus, etc)
- **Valor**: Informe o valor líquido que cai na conta
- **Tipo**: Fixo, Variável ou Extra
- **Recorrência**: Mensal, Única ou Anual
- **Pessoa**: Atribua a Pamela, Renato ou Família
- **Importante**: Deletar receitas agora afeta APENAS o mês filtrado (bug corrigido!)

### 2. 📥 Importar (Aba 2)
A mágica acontece aqui! Importe suas faturas de cartão ou extratos bancários.
- **Arquivos Suportados**: CSV do Itaú, Nubank e outros genéricos
- **Inteligência**: O sistema detecta automaticamente colunas de data, valor e descrição
- **Detecção Automática**: Extrai mês/ano do nome do arquivo (ex: `fatura-2026-02.csv`)
- **Data de Referência**: Você pode definir se aquela fatura pertence ao mês de "Fevereiro", mesmo que a compra tenha sido em "Janeiro"
- **Dono da Fatura**: Atribua a importação para "Renato" ou "Pamela" para separar os gastos

### 3. 📝 Transações (Aba 3)
O banco de dados completo de tudo que entrou e saiu.
- **Tabela Interativa**: Edite valores, nomes e categorias direto na tela, como no Excel
- **Mágico de Categorização** 🧙‍♂️:
    - Busca transações não categorizadas (ou todas)
    - Sugere categorias baseadas em regras + aprendizado de máquina
    - Aprende com suas escolhas anteriores
    - Você pode editar sugestões manualmente
    - Salva automaticamente ao aplicar
- **Ordenação Poderosa**:
    - Use o menu **"Ordenar por"** para organizar por Data, Valor, Categoria, Descrição ou Pessoa
    - Escolha **Crescente** ou **Decrescente**
- **Filtros**: Busque por nome (ex: "Uber") ou filtre por pessoa/mês/ano

### 4. 📊 Dashboard (Aba 4 - MELHORADO!)
Visão gerencial dos seus gastos com layout reorganizado.

**KPIs Principais:**
- Total de Gastos do período
- Maior Categoria de gasto
- Quantidade de Compras

**Seção 1: Análise por Categoria**
- **Gráfico de Pizza**: Distribuição visual dos gastos (com percentuais)
- **Tabela Detalhada** (NOVO!):
    - Total gasto por categoria
    - Número de compras
    - Valor médio por transação
    - Percentual do total
    - Ordenação automática por maior gasto

**Seção 2: Análise por Local**
- Gráfico de barras horizontal dos Top 5 locais onde você mais gasta
- Valores formatados em R$ diretamente no gráfico

**Seção 3: Evolução Temporal**
- Gráfico de quanto você gastou por dia no mês
- Visualização clara da evolução diária

**Filtros Disponíveis:**
- Mês e Ano
- Pessoa (sidebar)
- Modo de visualização: Data da Compra vs Mês de Referência (Fatura)

### 5. 🎯 Planejamento (Aba 5)
Defina metas e controle o orçamento.
- **Metas Individuais**:
    - Selecione **"Renato"** na barra lateral para definir o orçamento dele
    - Selecione **"Pamela"** para definir o dela
    - Cada um tem suas próprias metas (ex: R$ 500 de Lazer para um, R$ 300 para outro)
- **Visão Família**: Selecione **"Todos"** para ver a soma das metas e o gasto total da casa
- **Barras de Progresso**: Acompanhe visualmente se está estourando o limite de alguma categoria

### 6. 🔮 Projeções (Aba 6)
O futuro do seu dinheiro.
- **Fluxo de Caixa**: Compara **Entradas (Receitas)** vs **Saídas (Gastos Reais)** mês a mês
- **Acumulado Líquido (Linha Azul)**: Mostra se o patrimônio da família está crescendo ou diminuindo ao longo do ano
- **Cards de Resumo**:
    - **Receita Anual**: Quanto ganhou no ano
    - **Despesa Anual**: Quanto gastou no ano
    - **Saldo Líquido**: Quanto sobrou (ou faltou)
- **Filtro de Pessoa**: Veja o fluxo de caixa individual ou da família toda

---

## 💾 Onde os Dados São Salvos?

Todas as alterações são salvas automaticamente nos seguintes arquivos **locais**:
- `base_financeira.csv`: Todas as transações (compras, gastos)
- `receitas.csv`: Histórico de rendas mensais
- `settings.json`: Categorias e orçamentos personalizados

**🔒 Privacidade**: Estes arquivos ficam APENAS no seu computador e NÃO são enviados ao GitHub.

Para detalhes completos sobre persistência de dados, veja [`DATA_PERSISTENCE.md`](DATA_PERSISTENCE.md).

---

## 🔧 Dicas de Uso

1. **Backup Regular**: Copie os arquivos `.csv` e `.json` para uma pasta de backup
2. **Categorize Regularmente**: Use o Mágico de Categorização após importar faturas
3. **Defina Metas Realistas**: No Planejamento, comece com metas alcançáveis e ajuste mensalmente
4. **Filtro de Pessoa**: Use o filtro global da sidebar para alternar entre visões individuais e familiar

---

## 🐛 Problemas Resolvidos

- ✅ **Bug de Receitas**: Deletar de um mês não afeta mais outros meses (corrigido!)
- ✅ **Dashboard Confuso**: Agora com tabela detalhada e layout em seções claras
