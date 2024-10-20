import dotenv
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from PIL import Image
from transformers import AutoTokenizer, AutoFeatureExtractor
import torch
import os
folder_path = "head_movement_frames"
CHROMA_PATH = "Questions_db"

dotenv.load_dotenv()

class ImageEmbedder:
    def __init__(self, model_name="google/vit-base-patch16-224"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.feature_extractor = AutoFeatureExtractor.from_pretrained(model_name)
    
    def create_embeddings(self, image_path):
        image = Image.open(image_path)
        inputs = self.feature_extractor(images=image, return_tensors="pt")
        with torch.no_grad():
            embeddings = self.tokenizer.encode(inputs['pixel_values'].squeeze().tolist(), add_special_tokens=True)
        return embeddings

class ImageDocument:
    def __init__(self, image_path, metadata=None):
        self.image_path = image_path
        self.metadata = metadata or {}

image_embedder = ImageEmbedder()

# Assume we have a list of image paths
image_paths = [image_path for image_path in os.listdir(folder_path) if image_path.endswith(('.jpg', '.jpeg', '.png'))]  # Replace with your actual image paths

# Create image documents
image_documents = [ImageDocument(image_path) for image_path in image_paths]

# Create embeddings for each image
embeddings = [image_embedder.create_embeddings(doc.image_path) for doc in image_documents]

# Create Chroma vector store
image_vector_db = Chroma.from_embeddings(
    embeddings, OpenAIEmbeddings(), persist_directory=CHROMA_PATH
)
