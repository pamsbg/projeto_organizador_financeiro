"""
Módulo de aprendizado de padrões para categorização de transações.
Aprende com transações já categorizadas manualmente pelo usuário.
"""
import pandas as pd
from collections import defaultdict

def learn_patterns_from_data(df):
    """
    Analisa o DataFrame e cria um mapeamento de palavras-chave -> categoria
    baseado em transações já categorizadas manualmente.
    """
    patterns = defaultdict(lambda: defaultdict(int))
    
    # Filtra apenas transações que não são "Outros" ou "Pagamento/Crédito"
    valid_cats = df[~df['category'].isin(['Outros', 'Pagamento/Crédito', '', None])]
    
    for idx, row in valid_cats.iterrows():
        title = str(row['title']).lower()
        category = row['category']
        
        # Extrai palavras-chave significativas (ignora palavras muito curtas)
        words = [w.strip() for w in title.split() if len(w.strip()) > 2]
        
        for word in words:
            patterns[word][category] += 1
    
    # Converte para o padrão mais comum para cada palavra
    learned = {}
    for word, cat_counts in patterns.items():
        if cat_counts:
            # Pega a categoria mais frequente para essa palavra
            most_common = max(cat_counts.items(), key=lambda x: x[1])
            if most_common[1] >= 2:  # Pelo menos 2 ocorrências para confiar
                learned[word] = most_common[0]
    
    return learned

def suggest_category_from_learned(title, learned_patterns):
    """
    Tenta sugerir uma categoria baseado nos padrões aprendidos.
    Retorna None se não tiver confiança suficiente.
    """
    if not learned_patterns or not title:
        return None
    
    title_lower = str(title).lower()
    words = [w.strip() for w in title_lower.split() if len(w.strip()) > 2]
    
    # Conta votos de cada palavra
    votes = defaultdict(int)
    for word in words:
        if word in learned_patterns:
            votes[learned_patterns[word]] += 1
    
    if votes:
        # Retorna a categoria com mais votos SOMENTE se tiver pelo menos 2 votos
        # Isso evita categorizações erradas baseadas em uma única palavra ambígua
        best_match = max(votes.items(), key=lambda x: x[1])
        if best_match[1] >= 2:  # Pelo menos 2 palavras concordam
            return best_match[0]
    
    return None
