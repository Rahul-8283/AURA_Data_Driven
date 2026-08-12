import logging
from app.services.graph.extractor import extract_triplets_from_text

logging.basicConfig(level=logging.INFO)

def run_test():
    sample_text = (
        "In this study, we investigated the use of Magnesium as a dopant in NMC811 cathodes. "
        "We found that Mg significantly mitigates cation mixing, which is a major degradation "
        "mode that NMC811 typically suffers from. Furthermore, the material exhibits high capacity."
    )
    
    print("\n--- Testing Gemini Triplet Extraction ---")
    print(f"Input Text:\n{sample_text}\n")
    print("Extracting (this may take a few seconds)...\n")
    
    triplets = extract_triplets_from_text(sample_text)
    
    if not triplets:
        print("❌ No triplets extracted or an error occurred.")
        return

    print(f"✅ Successfully extracted {len(triplets)} triplets:")
    for i, t in enumerate(triplets):
        print(f"  {i+1}. ({t.subject_label}: {t.subject}) -[{t.predicate}]-> ({t.object_label}: {t.object})")

if __name__ == "__main__":
    run_test()
