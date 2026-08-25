from backend.knowledge.knowledge_base import KnowledgeBase

knowledge_base=KnowledgeBase()

questions=[
    "What is Python?",
    "Tell me about artificial intelligence",
    "What is binary searching?",
    "What is an operating system?",
    "Tell me about chess"
]

for question in questions:
    result=knowledge_base.search(question)

    print("\nQuestion:",question)

    if result:
        print("Topic:",result["topic"])
        print("Answer:",result["content"])
    else:
        print("No information found.")