import numpy as np
import os
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

# Устройство (GPU если доступен)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Загрузка модели CLIP
model = CLIPModel.from_pretrained("openai/clip-vit-large-patch14").to(device)
processor = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14")

# Функция для получения эмбеддинга изображения
def get_clip_embedding(image_path):
    image = Image.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt").to(device)
    with torch.no_grad():
        embedding = model.get_image_features(**inputs)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)
    return embedding.cpu().numpy()

# Сохранение эмбеддингов для всех изображений в папке
def save_embeddings(image_folder, output_folder):
    embeddings = {}
    
    for image_name in os.listdir(image_folder):
        if image_name.lower().endswith(('.jpg', '.jpeg', '.png')):
            image_path = os.path.join(image_folder, image_name)
            embedding = get_clip_embedding(image_path)
            embeddings[image_name] = embedding

            # Сохранение эмбеддинга в файл
            np.save(os.path.join(output_folder, f"{image_name}.npy"), embedding)
    
    print(f"Эмбеддинги для изображений из {image_folder} сохранены в {output_folder}.")
    return embeddings

# Пример использования
image_folder = r"A:\AI\my_landmark_bot\cv_service\references\dataset"  # Папка с изображениями
output_folder = r"A:\AI\my_landmark_bot\cv_service\references"  # Папка для сохранения эмбеддингов

os.makedirs(output_folder, exist_ok=True)
save_embeddings(image_folder, output_folder)
