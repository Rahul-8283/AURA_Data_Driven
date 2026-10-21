import numpy as np

from app.services.embeddings import EMBEDDING_DIM, embed_texts


def test_local_embedding_shape_and_normalization():
    vectors = np.array(embed_texts(["Hello world", "Cobalt-free cathode doping"]))

    assert vectors.shape == (2, EMBEDDING_DIM)
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-4)


if __name__ == "__main__":
    test_local_embedding_shape_and_normalization()
    print("Local embedding OK:", EMBEDDING_DIM, "dimensions, normalized")
