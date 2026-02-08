# 💰 Organizador Financeiro

Aplicativo de controle financeiro pessoal e familiar desenvolvido em Python com [Streamlit](https://streamlit.io/).

## 🌟 Funcionalidades

- **Dashboard Interativo**: Visão geral de gastos, receitas e saldo.
- **Importação Inteligente**: Importe faturas de cartão (CSV) e extratos bancários.
- **Categorização Automática**: O sistema aprende e categoriza suas compras (Mercado, Lazer, Transporte, etc.).
- **Planejamento Financeiro**: Defina metas de gastos por categoria e por pessoa.
- **Multi-Usuário**: Separe ou unifique a visão financeira de membros da família (ex: Renato e Pamela).
- **Projeções**: Acompanhe o fluxo de caixa e o crescimento do patrimônio ao longo do ano.

## 🚀 Como Rodar o Projeto

### Pré-requisitos
- Python 3.8+
- Pip

### Instalação

1.  Clone o repositório:
    ```bash
    git clone https://github.com/SEU_USUARIO/projeto_organizador_financeiro.git
    cd projeto_organizador_financeiro
    ```

2.  Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```

3.  Execute a aplicação:
    ```bash
    streamlit run app.py
    ```

## 📖 Manual de Uso
Para detalhes sobre como usar cada aba do sistema, consulte o [Manual de Uso](manual_de_uso.md).

## 🔒 Privacidade
Este projeto foi configurado para **não** enviar seus dados financeiros para o GitHub. Todos os arquivos CSV, Excel e JSON são ignorados pelo `.gitignore` e permanecem apenas no seu computador local.
