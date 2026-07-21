"""Quick test for Phase 2 RAG retriever."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from app.services.rag_retriever import rag_retriever

query = "Your bank KYC has expired update now at this link or account will be blocked"
results = rag_retriever.retrieve_fraud_patterns(query)

print(f"\nQuery: {query}")
print(f"Retrieved {len(results)} patterns:\n")
for i, r in enumerate(results):
    print(f"  {i+1}. [{r['fraud_type']}] relevance={r['relevance_score']:.2%}")
    print(f"     {r['content'][:150]}...")
    print()
