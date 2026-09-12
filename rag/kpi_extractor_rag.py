import os

from dotenv import load_dotenv
from pydantic import BaseModel, field_validator, Field

from llm.embeddings import FastEmbedEmbeddings
from llm.groq_llm import get_structured_completion
from vectorstore.qdrant_store import QdrantVectorStore, Retriever

load_dotenv()


class FinancialMetrics(BaseModel):
    revenue: str | int | None = Field(None, alias="Revenue")
    net_income: str | int | None = Field(None, alias="Net Income")
    operating_income: str | int | None = Field(None, alias="Operating Income")
    cash_flow: str | int | None = Field(None, alias="Cash Flow from Operating Activities")
    total_assets: str | int | None = Field(None, alias="Total Assets")
    total_liabilities: str | int | None = Field(None, alias="Total Liabilities")
    risk_factors: str | list | None = Field(None, alias="Top Risk Factors")
    growth_drivers: str | list | None = Field(None, alias="Top Growth Drivers")


# Groq's free tier caps requests at ~8000 tokens/minute, so context is kept small.
MAX_CONTEXT_CHARS = 10000


def retrieve_context(
    retriever: Retriever,
    company: str,
    year: int,
    top_k: int = 6
) -> str:
    """
    Retrieve broad financial context from the vector store.
    """
    query = f"""
    Annual report financial statements,
    income statement,
    balance sheet,
    cash flow statement,
    risks,
    growth drivers,
    financial performance
    for {company} fiscal year {year}
    """

    documents = retriever.invoke(
        query=query,
        company=company,
        year=year,
        top_k=top_k
    )

    context = "\n\n".join(
        doc.page_content
        for doc in documents
    )

    return context[:MAX_CONTEXT_CHARS]


def build_extraction_prompt(
    company: str,
    year: int,
    context: str
) -> str:
    """
    Build KPI extraction prompt.
    """
    return f"""
You are an expert financial analyst.

Company: {company}
Year: {year}

Context:
{context}

Extract the following information and return it as a JSON object with exactly these keys:

- "Revenue"
- "Net Income"
- "Operating Income"
- "Cash Flow from Operating Activities"
- "Total Assets"
- "Total Liabilities"
- "Top Risk Factors"
- "Top Growth Drivers"

Instructions:

- Use only the provided context.
- Return null for a key if the value is unavailable.
- Financial values must match the report exactly.
- Risk factors should be concise.
- Growth drivers should be concise.
- Return valid JSON only, using the exact keys listed above.
"""


def extract_financial_metrics(
    retriever: Retriever,
    company: str,
    year: int
) -> dict:
    """
    Extract KPIs using RAG.
    """
    context = retrieve_context(
        retriever=retriever,
        company=company,
        year=year
    )

    prompt = build_extraction_prompt(
        company=company,
        year=year,
        context=context
    )

    metrics = get_structured_completion(
        prompt=prompt,
        response_model=FinancialMetrics
    )

    return metrics.model_dump()


def main() -> None:
    company = "Apple"
    year = 2024

    vector_store = QdrantVectorStore(
        collection_name=os.getenv("QDRANT_COLLECTION", "investor-intelligence")
    )

    retriever = vector_store.as_retriever(FastEmbedEmbeddings())

    results = extract_financial_metrics(
        retriever=retriever,
        company=company,
        year=year
    )

    print(f"\nExtracted KPIs for {company} {year}\n")

    for key, value in results.items():
        print(f"{key}:")
        print(value)
        print("-" * 80)


    from database.save_metrics import save_metrics

    save_metrics(
        company=company,
        year=year,
        metrics=results
    )

if __name__ == "__main__":
    main()