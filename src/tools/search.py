"""Hybrid dense/sparse transcript retrieval pipeline."""

from langchain_classic.retrievers import ContextualCompressionRetriever, MergerRetriever
from langchain_cohere import CohereRerank
from langchain_community.document_transformers import LongContextReorder
from langchain_community.retrievers import BM25Retriever
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnablePassthrough
from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from src.models.llm_client import llm
from src.prompts.system_prompts import QA_PROMPT
from src.utils.helpers import format_timestamp


def build_search_chain(vectorstore, documents, memory, video_id: str):
    video_filter = Filter(
        must=[
            FieldCondition(
                key="metadata.video_id",
                match=MatchValue(value=video_id),
            )
        ]
    )
    dense = vectorstore.as_retriever(
        search_kwargs={"k": 6, "filter": video_filter}
    )
    sparse = BM25Retriever.from_documents(documents)
    sparse.k = 6
    merged = MergerRetriever(retrievers=[dense, sparse])
    reranked = ContextualCompressionRetriever(
        base_retriever=merged,
        base_compressor=CohereRerank(model="rerank-english-v3.0", top_n=5),
    )
    reorder = LongContextReorder()

    def history(_):
        return memory.load_memory_variables({}).get("history", "")

    def format_context(retrieved_documents):
        reordered = reorder.transform_documents(retrieved_documents)
        return "\n\n".join(
            f"[{format_timestamp(document.metadata.get('start', 0))}] "
            f"{document.page_content}"
            for document in reordered
        )

    inputs = RunnableParallel(
        {
            "history": RunnableLambda(history),
            "context": reranked | RunnableLambda(format_context),
            "question": RunnablePassthrough(),
        }
    )
    prompt = PromptTemplate(
        template=QA_PROMPT,
        input_variables=["history", "context", "question"],
    )
    return inputs | prompt | llm | StrOutputParser()
