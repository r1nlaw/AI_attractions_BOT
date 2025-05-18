import os
import logging
import aiohttp
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from config import BOT_TOKEN

# Логирование и папка для фото
logging.basicConfig(level=logging.INFO)
os.makedirs("photos", exist_ok=True)

# Список достопримечательностей
landmarks = {
    "Кинотеатр Симферополь": "kinoteatr_simf",
    "Памятник Екатерине II": "ekaterina_2",
    "Памятник Амет-Хану Султану": "pamatnik_amet_han_sultan",
    "Сквер имени Тренёва": "scver_trenev",
    "Александро-Невский собор": "sobor_alex_nevs",
    "Долгоруковский обелиск": "dolgoruk_obelisk",
    "Дом Воронцова": "dom_voronsova",
    "Кенасса в Симферополе": "kenassa_simf",
    "Кебир-Джами": "mechet_kebir_dzhami"
}

def get_landmarks_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton(name)] for name in landmarks], resize_keyboard=True)

start_keyboard = ReplyKeyboardMarkup([[KeyboardButton("🚀 Старт")]], resize_keyboard=True, one_time_keyboard=True)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["started"] = True
    await update.message.reply_text("Привет! Нажми 'Старт', чтобы начать.", reply_markup=start_keyboard)

# Обработка кнопки "Старт"
async def handle_start_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("started"):
        await update.message.reply_text("Для начала работы введите /start")
        return

    await update.message.reply_text("Выбери достопримечательность из списка:", reply_markup=get_landmarks_keyboard())

# Выбор достопримечательности
async def handle_landmark_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("started"):
        await update.message.reply_text("❗ Неизвестная команда. Введите /start для начала работы.")
        return

    text = update.message.text
    if text in landmarks:
        context.user_data["selected_landmark"] = landmarks[text]
        await update.message.reply_text(
            f"Ты выбрал: {text}. Теперь пришли фото этой достопримечательности.",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text("Пожалуйста, выбери достопримечательность из списка:", reply_markup=get_landmarks_keyboard())

# Фото
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("started"):
        await update.message.reply_text("Сначала введите /start")
        return

    target = context.user_data.get("selected_landmark")
    if not target:
        await update.message.reply_text("Сначала выбери достопримечательность.")
        return

    photo_file = await update.message.photo[-1].get_file()
    photo_path = f"photos/{photo_file.file_id}.jpg"
    await photo_file.download_to_drive(photo_path)

    # Отправляем фото и код достопримечательности на Flask-сервер
    async with aiohttp.ClientSession() as session:
        with open(photo_path, "rb") as f:
            data = aiohttp.FormData()
            data.add_field("image", f, filename="photo.jpg", content_type="image/jpeg")
            try:
                async with session.post(f"http://localhost:8005/verify?target={target}", data=data) as resp:
                    if resp.status == 200:
                        response = await resp.json()
                        result = response.get("result", "Не удалось получить результат.")
                        await update.message.reply_text(f"✅ Результат: {result}")
                    elif resp.status == 400:
                        await update.message.reply_text("🚫 Не та достопримечательность.")
                    else:
                        error = await resp.json()
                        await update.message.reply_text(f"⚠️ Ошибка: {error.get('error', 'Неизвестная ошибка')}")

            except Exception as e:
                await update.message.reply_text(f"❌ Не удалось связаться с сервером: {str(e)}")

    os.remove(photo_path)
    context.user_data.pop("selected_landmark", None)
    await update.message.reply_text("Можешь выбрать новую достопримечательность:", reply_markup=get_landmarks_keyboard())

# Обработка неизвестных текстов
async def handle_unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("started"):
        await update.message.reply_text("❗ Неизвестная команда. Для начала работы введите /start")
        return

    if context.user_data.get("selected_landmark"):
        await update.message.reply_text("Сейчас нужно отправить фото выбранной достопримечательности.")
    else:
        await update.message.reply_text("Пожалуйста, выбери достопримечательность из списка:", reply_markup=get_landmarks_keyboard())

# Запуск
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^🚀 Старт$"), handle_start_button))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_landmark_choice))
    app.add_handler(MessageHandler(filters.ALL, handle_unknown_text))  # fallback

    logging.info("Бот запущен...")
    app.run_polling()
