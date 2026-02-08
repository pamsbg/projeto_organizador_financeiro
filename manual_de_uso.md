# 📘 Manual de Uso - Organizador Financeiro

Bem-vindo ao **Organizador Financeiro Família Guerra Possas**! Este documento explica como rodar o sistema e como aproveitar cada funcionalidade.

## 🚀 Como Rodar o Sistema Localmente

Para iniciar o aplicativo no seu computador, abra o terminal na pasta do projeto e execute o seguinte comando:

```bash
python3.14 -m streamlit run app.py
```

O navegador abrirá automaticamente com o sistema pronto para uso.

---

## 🛠️ Funcionalidades e Abas

### 1. 🏠 Receitas (Aba 1)
Aqui você cadastra as **Rendas Mensais Fixas** da família.
- **Renda Líquida**: Informe o valor que cai na conta.
- **Dono**: Defina de quem é a renda (Renato, Pamela, etc).
- **Dados Salvos**: O sistema usa esses dados para calcular as projeções de futuro.

### 2. 📥 Importar (Aba 2)
A mágica acontece aqui! Importe suas faturas de cartão ou extratos bancários.
- **Arquivos Suportados**: CSV do Itaú, Nubank e outros genéricos.
- **Inteligência**: O sistema detecta automaticamente colunas de data, valor e descrição.
- **Data de Referência**: Você pode definir se aquela fatura pertence ao mês de "Fevereiro", mesmo que a compra tenha sido em "Janeiro".
- **Dono da Fatura**: Atribua a importação para "Renato" ou "Pamela" para separar os gastos.

### 3. 📝 Transações (Aba 3)
O banco de dados completo de tudo que entrou e saiu.
- **Tabela Interativa**: Edite valores, nomes e categorias direto na tela, como no Excel.
- **Ordenação Poderosa**:
    - Use o menu **"Ordenar por"** para organizar por Data, Valor ou Categoria.
    - Escolha **Crescente** ou **Decrescente**.
- **Filtros**: Busque por nome (ex: "Uber") ou filtre por pessoa/mês.

### 4. 📊 Dashboard (Aba 4)
Visão gerencial dos seus gastos.
- **KPIs**: Total Gasto, Maior Categoria e Quantidade de Compras.
- **Gráficos**:
    - **Pizza**: Para ver onde o dinheiro está indo (Categorias).
    - **Barra Lateral**: Top 5 locais onde você mais gasta.
    - **Evolução Diária**: Quanto você gastou por dia no mês.
- **Filtros**: Tudo isso pode ser filtrado por Mês, Ano e Pessoa.

### 5. 🎯 Planejamento (Aba 5)
Defina metas e controle o orçamento.
- **Metas Individuais**:
    - Selecione **"Renato"** na barra lateral para definir o orçamento dele.
    - Selecione **"Pamela"** para definir o dela.
    - Cada um tem suas próprias metas (ex: R$ 500 de Lazer para um, R$ 300 para outro).
- **Visão Família**: Selecione **"Todos"** para ver a soma das metas e o gasto total da casa.
- **Barras de Progresso**: Acompanhe visualmente se está estourando o limite de alguma categoria.

### 6. 🔮 Projeções (Aba 6)
O futuro do seu dinheiro.
- **Fluxo de Caixa**: Compara **Entradas (Receitas)** vs **Saídas (Gastos Reais)** mês a mês.
- **Acumulado Líquido (Linha Azul)**: Mostra se o patrimônio da família está crescendo ou diminuindo ao longo do ano.
- **Cards de Resumo**:
    - **Receita Anual**: Quanto ganhou no ano.
    - **Despesa Anual**: Quanto gastou no ano.
    - **Saldo Líquido**: Quanto sobrou (ou faltou).
- **Filtro de Pessoa**: Veja o fluxo de caixa individual ou da família toda.

---

## 💾 Salvamento Automático
Todas as alterações em tabelas e importações são salvas automaticamente nos arquivos:
- `base_financeira.csv`: Todas as transações.
- `settings.json`: Categorias, orçamentos e rendas cadastradas.
- `income.json`: Histórico de rendas.

**Dica**: Faça backups periódicos desses arquivos se desejar segurança extra!
