import re

def tokenize(text):
    return set(re.findall(r"\b\w+\b",text.lower()))

def calculate_score(query,item):
    query_words=tokenize(query)

    score=0

    for keyword in item["keywords"]:
        keyword_words=tokenize(keyword)

        for word in keyword_words:
            if word in query_words:
                score+=1

    topic_words=tokenize(item["topic"])

    for word in topic_words:
        if word in query_words:
            score+=2

    return score

def search_knowledge(query,knowledge):
    results=[]

    for item in knowledge:
        score=calculate_score(query,item)

        if score>0:
            results.append((score,item))

    results.sort(key=lambda x:x[0],reverse=True)

    return results