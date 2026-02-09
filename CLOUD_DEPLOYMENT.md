# 🌐 Guia de Deploy Cloud

## Visão Geral

Este aplicativo está configurado para funcionar tanto **localmente** quanto no **Streamlit Cloud** com persistência automática de dados.

## Como Funciona a Persistência

### Localmente
- Dados salvos diretamente em `base_financeira.csv`, `receitas.csv`, `settings.json`
- Nenhum commit automático

### No Streamlit Cloud
- **Auto-commit ativado**: Mudanças são automaticamente commitadas e enviadas ao GitHub
- Dados persistem entre recarregamentos e deploys
- Funciona porque o repositório é **privado**

## 🚀 Deploy Inicial

### 1. Preparar Repositório

```bash
# 1. Verificar que .gitignore está atualizado (permitindo CSVs)
git status

# 2. Adicionar dados existentes
git add base_financeira.csv receitas.csv settings.json

# 3. Commit inicial
git commit -m "feat: adicionar dados para persistência em cloud"

# 4. Push para GitHub
git push origin main
```

### 2. Configurar no Streamlit Cloud

1. Acesse [share.streamlit.io](https://share.streamlit.io)
2. Conecte seu GitHub
3. Selecione o repositório `projeto_organizador_financeiro`
4. Branch: `main`
5. Main file: `app.py`
6. **Advanced settings** → Adicione secrets:
   ```toml
   password = "sua_senha_aqui"
   ```

### 3. Deploy

- Clique em "Deploy"
- Aguarde 2-3 minutos
- App estará disponível em: `https://seu-app.streamlit.app`

## 🔄 Workflow de Uso

### Fazendo Alterações no App Online

1. **Acesse o app** no Streamlit Cloud
2. **Faça login** com sua senha
3. **Edite dados** (adicione transação, categorize, etc)
4. **Salve** (botão "Salvar Alterações")
5. **Auto-commit** acontece automaticamente em background
6. **Dados persistem** mesmo após redeploy

### Sincronização com Local

Se você trabalha tanto local quanto cloud:

```bash
# Baixar mudanças do cloud
git pull origin main

# Fazer mudanças locais
streamlit run app.py

# Subir mudanças locais
git add .
git commit -m "update: alterações locais"
git push origin main
```

## 🔧 Como Funciona o Auto-Commit

### Detecção de Ambiente

```python
def is_cloud_environment():
    """Detecta se está no Streamlit Cloud"""
    return os.getenv('STREAMLIT_SHARING_MODE') is not None
```

### Processo Automático

Quando você salva dados no app cloud:

1. `save_data()` / `save_income_data()` / `save_settings()` são chamadas
2. Dados são salvos nos CSVs
3. `auto_commit_data()` é acionada
4. **Se estiver em cloud**:
   - `git add` nos arquivos CSV/JSON
   - `git commit -m "auto: atualização de dados"`
   - `git push` para GitHub
5. **Se estiver local**: nada acontece (você faz commit manual)

### Segurança

- ✅ Falhas silenciosas (não quebra o app)
- ✅ Timeout de 30s no push
- ✅ Só executa em ambiente cloud
- ✅ Senha em `.streamlit/secrets.toml` NÃO é versionada

## 🛡️ Segurança e Privacidade

### O Que Está no GitHub (Repo Privado)

| Item | Versionado? | Visível no GitHub? |
|------|-------------|-------------------|
| `app.py` | ✅ | ✅ (mas repo é privado) |
| `base_financeira.csv` | ✅ | ✅ (mas repo é privado) |
| `receitas.csv` | ✅ | ✅ (mas repo é privado) |
| `settings.json` | ✅ | ✅ (mas repo é privado) |
| `.streamlit/secrets.toml` | ❌ | ❌ (nunca versionado) |

### Camadas de Proteção

1. **Repositório Privado**: Só você tem acesso
2. **Sistema de Login**: App protegido por senha
3. **Secrets Separados**: Senha não está no código
4. **HTTPS**: Comunicação criptografada com Streamlit Cloud

## 🐛 Troubleshooting

### Dados não persistem após redeploy

**Causa**: Auto-commit pode ter falhado

**Solução**:
```bash
# Verificar logs do Streamlit Cloud
# Ou fazer commit manual
git add base_financeira.csv receitas.csv settings.json
git commit -m "fix: persistir dados manualmente"
git push
```

### Erro de permissão no git push

**Causa**: Streamlit Cloud precisa de permissão de escrita

**Solução**:
- Nas configurações do Streamlit Cloud, garantir que tem permissões de escrita no repo
- Ou desativar auto-commit e fazer commits manuais localmente

### App lento após muitos commits

**Causa**: Histórico do Git fica grande

**Solução futura**: Migrar para banco de dados (SQLite, Supabase, PostgreSQL)

## 🔮 Próximos Passos (Migração Futura)

Quando o app crescer, considere migrar para:

### Opção 1: SQLite
- Arquivo único `database.db`
- Ainda versionável no Git
- Mais eficiente que CSVs

### Opção 2: Supabase (PostgreSQL)
- Banco real na nuvem
- 500MB grátis
- API REST automática
- Sem necessidade de commits

### Opção 3: Google Sheets API
- Interface familiar (planilhas)
- Mais lento
- Bom para compartilhamento familiar

## 📊 Status Atual

✅ Auto-commit implementado  
✅ Funciona local + cloud  
✅ Senha protegida  
✅ Dados privados (repo privado)  
⏳ Migração para DB (futuro)

## 🔗 Links Úteis

- [Streamlit Cloud Docs](https://docs.streamlit.io/streamlit-community-cloud)
- [Secrets Management](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management)
- [Git para Dados](https://dvc.org/) (alternativa avançada)
