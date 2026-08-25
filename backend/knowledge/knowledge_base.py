from backend.knowledge.loader import load_knowledge
from backend.knowledge.search import search_knowledge

class KnowledgeBase:
    def __init__(self):
        self.knowledge=load_knowledge()

    def search(self,query):
        results=search_knowledge(
            query,
            self.knowledge
        )

        if not results:
            return None

        return results[0][1]