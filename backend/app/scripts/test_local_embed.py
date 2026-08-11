import chromadb.utils.embedding_functions as embedding_functions

def test_default_embedding():
    try:
        emb_fn = embedding_functions.DefaultEmbeddingFunction()
        emb = emb_fn(["Hello world"])
        print("Success! Dimensions:", len(emb[0]))
    except Exception as e:
        print("Error:", str(e))

if __name__ == "__main__":
    test_default_embedding()
