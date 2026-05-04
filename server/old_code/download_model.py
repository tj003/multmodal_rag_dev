# download_model.py
from huggingface_hub import snapshot_download

print("Downloading model directly to D drive...")

snapshot_download(
    repo_id="sentence-transformers/all-mpnet-base-v2",
    local_dir="D:/models/all-mpnet-base-v2",
    local_dir_use_symlinks=False
)

print("✅ Done! Verifying...")

# Verify it loads from D drive
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("D:/models/all-mpnet-base-v2")
test = model.encode(["hello world"])
print(f"✅ Model works! Embedding dims: {len(test[0])}")  # should be 768