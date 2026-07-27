import chromadb
from chromadb.utils import embedding_functions

# Initialize local persistent ChromaDB storage
client = chromadb.PersistentClient(path="./chroma_db")

# Use ChromaDB's default lightweight embedding function
default_ef = embedding_functions.DefaultEmbeddingFunction()

# Create or get the clinical cases vector collection
cases_collection = client.get_or_create_collection(
    name="clinical_cases",
    embedding_function=default_ef
)

def seed_initial_cases():
    """Seeds ChromaDB with initial benchmark cases if the collection is empty."""
    if cases_collection.count() == 0:
        cases_collection.add(
            documents=[
                "62yo female with sudden sharp tearing chest pain radiating to mid-back, BP mismatch 184/102 right arm vs 154/88 left arm, bounding right radial pulse, faint left radial pulse, soft diastolic murmur. Diagnosis: Acute Stanford Type A Aortic Dissection with aortic regurgitation.",
                "55yo male with severe crushing substernal chest pain, diaphoresis, ST-segment elevation in leads II, III, aVF. Diagnosis: Acute Inferior Myocardial Infarction.",
                "45yo male presenting with sudden onset pleuritic chest pain, dyspnea, tachycardia, recent 14-hour long-haul flight, swollen tender left calf. Diagnosis: Acute Pulmonary Embolism."
            ],
            metadatas=[
                {"condition": "Aortic Dissection", "severity": "Critical"},
                {"condition": "Inferior STEMI", "severity": "Critical"},
                {"condition": "Pulmonary Embolism", "severity": "High"}
            ],
            ids=["case_001", "case_002", "case_003"]
        )
        print("✅ Seeded initial clinical cases into ChromaDB.")

def get_similar_cases(query_text: str, n_results: int = 1) -> str:
    """Queries ChromaDB for similar past clinical cases and returns a formatted string."""
    try:
        results = cases_collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        if results and results.get("documents") and results["documents"][0]:
            matched_docs = results["documents"][0]
            return "\n".join([f"- {doc}" for doc in matched_docs])
    except Exception as e:
        print(f"ChromaDB Query Error: {e}")
    return "No matching past cases found."

# Run seeding on module import
seed_initial_cases()