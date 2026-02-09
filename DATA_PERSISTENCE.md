# 📦 Guia de Persistência de Dados

## Onde os Dados São Salvos?

Todos os dados do sistema são salvos **localmente** no seu computador, na mesma pasta do projeto. Nada é enviado para a nuvem ou servidores externos.

## 📁 Arquivos de Dados

O sistema utiliza 3 arquivos principais para persistência:

### 1. `base_financeira.csv` - Transações e Gastos

**Localização**: Raiz do projeto  
**Tipo**: CSV (texto simples separado por vírgulas)  
**Conteúdo**: Todas as transações financeiras (compras, despesas, pagamentos)

**Estrutura do arquivo:**
```csv
id,date,reference_date,title,amount,category,installment_info,owner
abc-123,2026-02-01,2026-02-01,Mercado Assai,150.50,Alimentação (Mercado/Sacolão),,Pamela
def-456,2026-02-03,2026-02-01,Uber,25.00,Transporte (Uber/99),,Renato
```

**Colunas:**
- `id`: Identificador único (UUID)
- `date`: Data da compra
- `reference_date`: Data de referência (mês da fatura)
- `title`: Descrição da transação
- `amount`: Valor em R$
- `category`: Categoria (Alimentação, Transporte, etc.)
- `installment_info`: Info de parcelamento (se houver)
- `owner`: Dono da transação (Pamela, Renato, Família)

**Gerenciado por:**
- `utils.py`: Funções `load_data()` e `save_data()`
- `app.py`: Aba "📝 Transações"

---

### 2. `receitas.csv` - Fontes de Renda

**Localização**: Raiz do projeto  
**Tipo**: CSV  
**Conteúdo**: Receitas mensais (salários, rendas extras, etc.)

**Estrutura do arquivo:**
```csv
date,source,amount,type,recurrence,owner
2026-02-01,Salario,15000,Fixo,Mensal,Pamela
2026-02-01,Salario,15000,Fixo,Mensal,Renato
```

**Colunas:**
- `date`: Data de entrada da renda
- `source`: Fonte (Salário, Bônus, Freelance, etc.)
- `amount`: Valor em R$
- `type`: Tipo (Fixo, Variável, Extra)
- `recurrence`: Recorrência (Mensal, Única, Anual)
- `owner`: Dono da receita (Pamela, Renato, Família)

**Gerenciado por:**
- `utils.py`: Funções `load_income_data()` e `save_income_data()`
- `app.py`: Aba "💰 Receitas"

---

### 3. `settings.json` - Configurações do Sistema

**Localização**: Raiz do projeto  
**Tipo**: JSON (texto em formato hierárquico)  
**Conteúdo**: Categorias personalizadas e metas de orçamento

**Estrutura do arquivo:**
```json
{
    "categories": [
        "Moradia",
        "Alimentação (Mercado/Sacolão)",
        "Transporte (Uber/99)",
        "Saúde/Farmácia",
        "Lazer/Restaurantes",
        "Outros"
    ],
    "budgets": {
        "default": {
            "Alimentação (Mercado/Sacolão)": 1200.0,
            "Transporte (Uber/99)": 300.0
        },
        "2026-02_Pamela": {
            "Alimentação (Mercado/Sacolão)": 600.0,
            "Lazer/Restaurantes": 400.0
        }
    }
}
```

**Seções:**
- `categories`: Lista de categorias disponíveis
- `budgets`: Metas de gasto organizadas por período e pessoa
  - `default`: Meta padrão (quando não há específica)
  - `YYYY-MM_Pessoa`: Meta específica para um mês e pessoa

**Gerenciado por:**
- `utils.py`: Funções `load_settings()` e `save_settings()`
- `app.py`: Sidebar (gerenciar categorias) e Aba "🎯 Planejamento"

---

## 🔄 Fluxo de Dados

### Como os Dados Fluem no Sistema:

```
┌────────────────────────────────────────────────────┐
│ 1. IMPORTAÇÃO                                      │
│    Usuário importa CSV do banco                    │
│    ↓                                                │
│    app.py (Aba Importar) → utils.process_uploaded │
│    ↓                                                │
│    Categorização automática                        │
│    ↓                                                │
│    Salvo em base_financeira.csv                    │
└────────────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────────────┐
│ 2. VISUALIZAÇÃO                                    │
│    app.py (Aba Dashboard/Transações)               │
│    ↓                                                │
│    utils.load_data() → Lê base_financeira.csv      │
│    ↓                                                │
│    Pandas DataFrame em memória (st.session_state)  │
│    ↓                                                │
│    Gráficos e tabelas exibidos                     │
└────────────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────────────┐
│ 3. EDIÇÃO                                          │
│    Usuário edita dados no st.data_editor           │
│    ↓                                                │
│    Clica "Salvar Alterações"                       │
│    ↓                                                │
│    utils.save_data() → Grava base_financeira.csv   │
└────────────────────────────────────────────────────┘
```

### Mesmo Fluxo para Receitas:

```
Usuário adiciona receita → st.data_editor → utils.save_income_data() → receitas.csv
```

### Fluxo de Configurações:

```
Usuário cria categoria → app.py atualiza dict → utils.save_settings() → settings.json
```

---

## 🔒 Segurança e Privacidade

### Dados Locais APENAS
- ✅ **Todos os dados ficam no seu computador**
- ✅ **Nada é enviado para a internet**
- ✅ **Arquivos CSV/JSON são legíveis em qualquer editor de texto**

### GitHub e Versionamento
O arquivo `.gitignore` está configurado para **NÃO** versionar dados:

```
# Dados financeiros (NÃO vão pro GitHub)
base_financeira.csv
base_financeira.bak
receitas.csv
settings.json
*.xlsx
faturas_*/
```

**Resultado:**
- ✅ Código do app é versionado
- ❌ Seus dados financeiros **NÃO** são enviados ao GitHub
- ✅ Cada pessoa tem seus próprios dados locais

---

## 🛡️ Backup dos Dados

### Como Fazer Backup

**Manualmente:**
1. Copie os arquivos:
   - `base_financeira.csv`
   - `receitas.csv`
   - `settings.json`
2. Cole em uma pasta segura (ex: Google Drive, OneDrive, HD externo)

**Automático (futuro):**
O sistema cria automaticamente `base_financeira.bak` em algumas operações, mas não é um sistema completo de backup.

### Como Restaurar Backup

1. Feche o aplicativo Streamlit
2. Substitua os arquivos atuais pelos do backup
3. Reinicie o aplicativo

---

## 🔧 Formato dos Arquivos

**Por que CSV e JSON?**

- ✅ **Legível**: Você pode abrir no Excel, Google Sheets, Notepad
- ✅ **Portável**: Funciona em Windows, Mac, Linux
- ✅ **Simples**: Fácil de fazer backup e transferir
- ✅ **Interoperável**: Pode usar em outras ferramentas (Python, R, Excel)

**Desvantagens (e por que são aceitáveis):**
- ❌ Não é um banco de dados "real" (SQLite, PostgreSQL)
- ✅ Mas para uso pessoal/familiar, CSV é mais que suficiente
- ❌ Não tem histórico de alterações automático
- ✅ Mas está no Git (apenas o código, não os dados)

---

## 📊 Tamanho dos Arquivos

**Estimativa para uso normal:**
- `base_financeira.csv`: ~10-50 KB (centenas de transações)
- `receitas.csv`: ~1-5 KB (dezenas de entradas)
- `settings.json`: ~1-2 KB

**1 ano de uso intenso:** ~100-200 KB total (insignificante)

---

## 💡 Perguntas Frequentes

### "Onde estão meus dados?"
Na pasta do projeto, ao lado do `app.py`. Arquivos: `base_financeira.csv`, `receitas.csv`, `settings.json`.

### "Posso abrir os arquivos manualmente?"
Sim! São arquivos de texto. Abra com Excel, Google Sheets, Notepad ou qualquer editor.

### "E se eu deletar um arquivo por acidente?"
Se não tiver backup, os dados são perdidos. Por isso, recomendamos backup regular.

### "Os dados vão pro GitHub?"
**NÃO**. O `.gitignore` bloqueia. Apenas o código do app é versionado.

### "Posso usar em múltiplos computadores?"
Sim, mas precisa copiar os arquivos CSV/JSON manualmente ou usar sincronização de pasta (Google Drive, OneDrive).

### "Posso migrar para um banco de dados?"
Sim! Os arquivos CSV podem ser importados facilmente para SQLite, PostgreSQL, MySQL, etc.

---

## 🔗 Arquivos Relacionados

- [`utils.py`](file:///c:/Users/pamsb/OneDrive/Área de Trabalho/projeto_organizador_financeiro/utils.py) - Funções de I/O de dados
- [`app.py`](file:///c:/Users/pamsb/OneDrive/Área de Trabalho/projeto_organizador_financeiro/app.py) - Interface e lógica de salvamento
- [`.gitignore`](file:///c:/Users/pamsb/OneDrive/Área de Trabalho/projeto_organizador_financeiro/.gitignore) - Proteção de dados no Git
