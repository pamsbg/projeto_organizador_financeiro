"""
Módulo de aprendizado de padrões para categorização de transações.
Aprende com transações já categorizadas manualmente pelo usuário.
"""
import pandas as pd
from collections import defaultdict
STOPWORDS = {
    'compra', 'pagamento', 'transferencia', 'transf', 'doc', 'ted', 'pix', 'envio', 'recebimento',
    'de', 'para', 'do', 'da', 'no', 'na', 'em', 'com', 'e', 'o', 'a', 'os', 'as', 'um', 'uma',
    'cartao', 'fatura', 'debito', 'credito', 'loja', 'supermercado', 'pagto', 'pgto', 'online',
    'app', 'mobile', 'internet', 'bank', 'banco', 'servico', 'serv', 'saque', 'extrato'
}

def tokenize(text):
    """Quebra o texto em palavras significativas."""
    if not text: return []
    text = str(text).lower().replace('/', ' ').replace('-', ' ').replace('.', ' ')
    words = [w.strip() for w in text.split() if len(w.strip()) > 2]
    return [w for w in words if w not in STOPWORDS and not w.isdigit()]

def learn_patterns_from_data(df, history_df=None):
    """
    Analisa os DataFrames e cria um mapeamento de palavras-chave -> categoria.
    df: Transações atuais (memória curta).
    history_df: Dataset persistente da planilha (memória longa/feedbacks).
    """
    patterns = defaultdict(lambda: defaultdict(int))
    amount_patterns = defaultdict(lambda: defaultdict(int)) # Novo: Padrões de valor exato
    
    # 1. Processar Histórico (Peso maior: 5x)
    if history_df is not None and not history_df.empty:
        # Garantir colunas
        if 'Descricao' in history_df.columns and 'Categoria' in history_df.columns:
            for idx, row in history_df.iterrows():
                title = str(row['Descricao'])
                category = row['Categoria']
                if not category: continue
                
                # Aprendizado por Valor Exato (se disponível)
                if 'Valor' in row and row['Valor']:
                    try:
                        val = float(str(row['Valor']).replace(',', '.'))
                        if val > 0:
                            amount_patterns[val][category] += 5
                    except: pass

                words = tokenize(title)
                for word in words:
                    patterns[word][category] += 5 # Peso 5 para correções explícitas (feedback direto)
    
    # 2. Processar Dados Atuais (Peso normal: 1x)
    if not df.empty:
        # Filtra apenas transações que não são "Outros" ou "Pagamento/Crédito"
        valid_cats = df[~df['category'].isin(['Outros', 'Pagamento/Crédito', '', None])]
        
        for idx, row in valid_cats.iterrows():
            title = str(row['title'])
            category = row['category']
            
            # Aprendizado por Valor Exato
            try:
                val = float(row['amount'])
                if val > 0:
                     amount_patterns[val][category] += 1
            except: pass
            
            words = tokenize(title)
            for word in words:
                patterns[word][category] += 1
    
    # Converte para o padrão mais comum para cada palavra/valor
    learned = {
        "words": {},
        "amounts": {}
    }
    
    for word, cat_counts in patterns.items():
        if cat_counts:
            most_common = max(cat_counts.items(), key=lambda x: x[1])
            if most_common[1] >= 2:  # Pelo menos 2 pontos de confiança
                learned["words"][word] = most_common[0]

    for val, cat_counts in amount_patterns.items():
        if cat_counts:
            most_common = max(cat_counts.items(), key=lambda x: x[1])
            # Exige mais confiança para valor exato (pelo menos 3 pontos), pois valores podem coincidir
            if most_common[1] >= 3: 
                learned["amounts"][val] = most_common[0]
                
    return learned

def suggest_category_from_learned(title, learned_patterns, amount=None):
    """
    Tenta sugerir uma categoria baseado nos padrões aprendidos.
    Prioridade: Valor Exato > Palavras-Chave.
    """
    if not learned_patterns:
        return None
        
    # 1. Tentar por Valor Exato
    if amount is not None:
        try:
            val = float(amount)
            if val in learned_patterns.get("amounts", {}):
                return learned_patterns["amounts"][val]
        except: pass
    
    # 2. Tentar por Palavras-Chave
    if not title: return None
    
    words = tokenize(title)
    
    # Conta votos de cada palavra
    word_patterns = learned_patterns.get("words", {})
    votes = defaultdict(int)
    for word in words:
        if word in word_patterns:
            votes[word_patterns[word]] += 1
    
    if votes:
        # Retorna a categoria com mais votos SOMENTE se tiver pelo menos 2 votos (ou 1 voto se for palavra muito específica?)
        # Vamos manter conservador: max votos
        best_match = max(votes.items(), key=lambda x: x[1])
        # Se hover empate ou poucos votos, talvez retornar None? 
        # Por enquanto retorna o melhor palpite
        return best_match[0]
    
    return None
