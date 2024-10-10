from typing import List, Union
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings

class ContextTool:
    def __init__(self):
        self.fixed_context = ""
        self.vector_db = None

    def set_fixed_context(self, context: str):
        self.fixed_context = context

    def create_vector_db(self, texts: List[str]):
        embeddings = OpenAIEmbeddings()
        self.vector_db = Chroma.from_texts(texts, embeddings)

    def query_context(self, query: str, k: int = 5) -> Union[str, List[str]]:
        if self.vector_db:
            return self.vector_db.similarity_search(query, k=k)
        else:
            return self.fixed_context

# # Usage:
# context_tool = ContextTool()
# curried_proxy.add_class_tool("context", context_tool)