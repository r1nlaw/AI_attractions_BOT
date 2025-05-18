import os
import torch
from sklearn.metrics.pairwise import cosine_similarity
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import numpy as np
from flask import Flask, request, jsonify
import tempfile

app = Flask(__name__)

# Настройки путей
current_directory = os.getcwd()
embeddings_folder = os.path.join(current_directory, "references")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Загрузка модели CLIP
model = CLIPModel.from_pretrained("openai/clip-vit-large-patch14").to(device)
processor = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14", use_fast=True)

# Функция получения эмбеддинга изображения
def get_clip_embedding(image_path):
    image = Image.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt").to(device)
    with torch.no_grad():
        embedding = model.get_image_features(**inputs)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)
    return embedding.cpu().numpy()

# Загружаем только нужные эмбеддинги
def load_embeddings_for_target(folder, target_landmark):
    embeddings = {}
    for file_name in os.listdir(folder):
        if file_name.endswith('.npy'):
            base_name = os.path.splitext(os.path.splitext(file_name)[0])[0]
            landmark_name = base_name.split("__")[0]
            if landmark_name.lower() == target_landmark.lower():
                path = os.path.join(folder, file_name)
                embeddings[file_name] = np.load(path)
    return embeddings

# Проверка на совпадение
def verify_target_landmark(query_embedding, target_landmark, embeddings, threshold=0.80, min_match_count=3):
    matches = []
    for file_name, ref_embedding in embeddings.items():
        similarity = cosine_similarity(query_embedding, ref_embedding)[0][0]
        if similarity >= threshold:
            matches.append(similarity)

    print(f"[{target_landmark}] найдено совпадений: {len(matches)}")
    return len(matches) >= min_match_count

# Роут обработки POST-запроса
@app.route("/verify", methods=["POST"])
def verify():
    target = request.args.get("target")
    if not target:
        return jsonify({"error": "Missing ?target= parameter"}), 400

    if "image" not in request.files:
        return jsonify({"error": "Missing image file"}), 400

    image_file = request.files["image"]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        image_path = tmp.name
        image_file.save(image_path)

    try:
        query_embedding = get_clip_embedding(image_path)
        embeddings = load_embeddings_for_target(embeddings_folder, target)

        if not embeddings:
            return jsonify({"error": f"No embeddings found for target '{target}'"}), 404

        matched = verify_target_landmark(
            query_embedding, target_landmark=target, embeddings=embeddings
        )

        if matched:
            return jsonify({"result": "Да, это та достопримечательность"}), 200
        else:
            return jsonify({"result": "Does not match"}), 400
    finally:
        os.remove(image_path)

# Запуск сервера
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8005, debug=True)
