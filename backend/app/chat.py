from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_ollama import ChatOllama
from .config import settings
from .vector_store import VectorStore


class ChatService:
    def __init__(
        self,
        vector_store: VectorStore,
        llm_model_name: str = settings.LLM_MODEL_NAME,
    ):
        self.vector_store = vector_store
        self.llm_model_name = llm_model_name
        self.llm = ChatOllama(model=llm_model_name, temperature=0.1)
        self.rag_chain = self._build_rag_chain()

    def _build_rag_chain(self):
        retriever = self.vector_store.get_retriever()

        system_prompt = """你是一个专业的问答助手，请基于以下提供的上下文信息来回答用户的问题。
如果上下文中没有相关信息，请诚实地说明你不知道答案，不要编造内容。
请用简洁、准确的中文回答问题。

上下文信息：
{context}
"""

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessage(content="{question}"),
            ]
        )

        def format_docs(docs: List[Document]) -> str:
            return "\n\n".join(doc.page_content for doc in docs)

        def get_question(input_dict: Dict[str, Any]) -> str:
            return input_dict["question"]

        context_chain = RunnableLambda(get_question) | retriever | format_docs

        chain = (
            RunnablePassthrough.assign(context=context_chain)
            | prompt
            | self.llm
            | StrOutputParser()
        )

        return chain

    def chat(
        self,
        question: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        history: List[BaseMessage] = []
        if chat_history:
            for msg in chat_history:
                if msg["role"] == "user":
                    history.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    history.append(AIMessage(content=msg["content"]))

        source_docs = self.vector_store.similarity_search_with_score(question)

        answer = self.rag_chain.invoke(
            {"question": question, "chat_history": history}
        )

        sources = [
            {
                "content": doc.page_content,
                "source": doc.metadata.get("source", "unknown"),
                "score": round(max(0, 1 - distance), 4),
            }
            for doc, distance in source_docs
        ]

        return {"answer": answer, "sources": sources}

    def chat_stream(
        self,
        question: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ):
        history: List[BaseMessage] = []
        if chat_history:
            for msg in chat_history:
                if msg["role"] == "user":
                    history.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    history.append(AIMessage(content=msg["content"]))

        for chunk in self.rag_chain.stream(
            {"question": question, "chat_history": history}
        ):
            yield chunk
