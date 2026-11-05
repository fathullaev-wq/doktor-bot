import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.markdown import html_decoration

# Sozlamalar
BOT_TOKEN = "8945909967:AAElxGb3HZEIZRn1GEHrOg4EvUKsf23F5PI"
DOCTOR_CHAT_ID = 1362874842  # Sizning Telegram ID raqamingiz

# Klinika geolokatsiyasi
CLINIC_LAT = 41.380194
CLINIC_LON = 69.277222

# Shifokor yopgan kunlar ro'yxati (Xotirada saqlanadi)
blocked_dates = set()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Holatlar (States)
class BookingState(StatesGroup):
    waiting_for_phone = State()

class HomeVisitState(StatesGroup):
    waiting_for_location = State()
    waiting_for_phone = State()

class DoctorConfirmState(StatesGroup):
    waiting_for_time_input = State()

# Klaviaturalar
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏰ Qabul vaqtlari | Время приема")],
            [KeyboardButton(text="📍 Manzil | Адрес")],
            [KeyboardButton(text="📝 Qabulga yozilish | Запись на прием")],
            [KeyboardButton(text="🏠 Uyga chaqiruv | Вызов на дом")],
        ],
        resize_keyboard=True,
    )

def get_phone_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Raqamni yuborish / Отправить номер", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def get_location_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Lokatsiyani yuborish / Отправить геолокацию", request_location=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def get_dates_keyboard():
    buttons = []
    today = datetime.now()
    days_uz = ["Dush", "Sesh", "Chor", "Pay", "Juma", "Shan", "Yak"]
    
    added_days = 0
    current_offset = 0
    
    # Yakshanba va Shifokor yopgan kunlarni o'tkazib yuborish
    while added_days < 6:
        date_obj = today + timedelta(days=current_offset)
        date_formatted = date_obj.strftime("%d.%m.%Y")
        
        # Yakshanba emas va Yopilgan kunlar ro'yxatida bo'lmasa ko'rsatiladi
        if date_obj.weekday() != 6 and date_formatted not in blocked_dates:
            day_str = days_uz[date_obj.weekday()]
            btn_text = f"{date_formatted} ({day_str})"
            buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"book_date_{date_formatted}")])
            added_days += 1
        current_offset += 1
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Admin Panel Klaviaturasi (Shifokor uchun kunlarni yopish)
def get_admin_dates_keyboard(action="block"):
    buttons = []
    today = datetime.now()
    days_uz = ["Dush", "Sesh", "Chor", "Pay", "Juma", "Shan", "Yak"]
    
    for i in range(10):  # Keyingi 10 kunni ko'rsatish
        date_obj = today + timedelta(days=i)
        if date_obj.weekday() != 6:
            date_formatted = date_obj.strftime("%d.%m.%Y")
            day_str = days_uz[date_obj.weekday()]
            status = "🔴 Yopilgan" if date_formatted in blocked_dates else "🟢 Ochiq"
            btn_text = f"{date_formatted} ({day_str}) - {status}"
            buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"{action}_date_{date_formatted}")])
            
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Handlerlar
@dp.message(CommandStart())
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Assalomu alaykum!\n"
        "Shifokor-nevropatolog Shoxruxning yordamchi botiga xush kelibsiz. "
        "Oʻzingizga kerakli boʻlimni tanlang!\n\n"
        "Здравствуйте!\n"
        "Добро пожаловать в бот-помощник врача-невропатолога Шохруха. "
        "Выберите нужный раздел!",
        reply_markup=get_main_keyboard(),
    )

# --- SHIFOKOR (ADMIN) PANEL BO'LIMI ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != DOCTOR_CHAT_ID:
        return
        
    ikb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔴 Kunni yopish (Dam olish)", callback_data="admin_block_menu")],
            [InlineKeyboardButton(text="🟢 Kunni qayta ochish", callback_data="admin_unblock_menu")],
            [InlineKeyboardButton(text="📋 Yopilgan kunlar ro'yxati", callback_data="admin_list_blocked")],
        ]
    )
    await message.answer("👨‍⚕️ <b>Shifokor kabineti / Admin Panel:</b>\n\nKerakli amalni tanlang:", reply_markup=ikb, parse_mode="HTML")

@dp.callback_query(F.data == "admin_block_menu")
async def admin_block_menu(callback: types.CallbackQuery):
    if callback.from_user.id != DOCTOR_CHAT_ID:
        return
    await callback.message.answer("🚫 <b>Yopmoqchi bo'lgan kuningizni tanlang:</b>", reply_markup=get_admin_dates_keyboard("block"), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_unblock_menu")
async def admin_unblock_menu(callback: types.CallbackQuery):
    if callback.from_user.id != DOCTOR_CHAT_ID:
        return
    await callback.message.answer("🔓 <b>Qayta ochmoqchi bo'lgan kuningizni tanlang:</b>", reply_markup=get_admin_dates_keyboard("unblock"), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("block_date_"))
async def process_block_date(callback: types.CallbackQuery):
    if callback.from_user.id != DOCTOR_CHAT_ID:
        return
    selected_date = callback.data.split("block_date_")[1]
    blocked_dates.add(selected_date)
    await callback.message.answer(f"✅ <b>{selected_date}</b> sanasi qabul uchun yopildi! Bemorlar bu kunga yozila olishmaydi.", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("unblock_date_"))
async def process_unblock_date(callback: types.CallbackQuery):
    if callback.from_user.id != DOCTOR_CHAT_ID:
        return
    selected_date = callback.data.split("unblock_date_")[1]
    blocked_dates.discard(selected_date)
    await callback.message.answer(f"🟢 <b>{selected_date}</b> sanasi qayta ochildi!", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_list_blocked")
async def process_list_blocked(callback: types.CallbackQuery):
    if callback.from_user.id != DOCTOR_CHAT_ID:
        return
    if not blocked_dates:
        await callback.message.answer("📋 Hozircha hech qaysi sana yopilmagan.")
    else:
        dates_str = "\n".join([f"• {d}" for d in sorted(blocked_dates)])
        await callback.message.answer(f"📌 <b>Yopilgan kunlar ro'yxati:</b>\n\n{dates_str}", parse_mode="HTML")
    await callback.answer()

# --- BEMORLAR BO'LIMI ---
@dp.message(F.text == "⏰ Qabul vaqtlari | Время приема")
async def schedule_handler(message: types.Message):
    await message.answer(
        "⏰ <b>Qabul vaqtlari / Время приема:</b>\n\n"
        "🗓 <b>Dushanba – Shanba / Понедельник – Суббота:</b>\n"
        "🕒 17:00 – 20:00\n"
        "<i>(Qabul jonli navbat tartibida amalga oshiriladi / Прием в порядке живой очереди)</i>\n\n"
        "🔴 <b>Yakshanba / Воскресенье:</b>\n"
        "🚫 Dam olish kuni / Выходной день",
        parse_mode="HTML",
    )

@dp.message(F.text == "📍 Manzil | Адрес")
async def location_handler(message: types.Message):
    await message.answer_venue(
        latitude=CLINIC_LAT,
        longitude=CLINIC_LON,
        title="Shifokor-nevropatolog Qabuli",
        address="Toshkent shahri",
    )

# Qabulga yozilish jarayoni
@dp.message(F.text == "📝 Qabulga yozilish | Запись на прием")
async def booking_start(message: types.Message):
    await message.answer(
        "📝 Qabulga qaysi kuni kelmoqchisiz? Sanani tanlang! <i>(Qabul jonli navbat tartibida)</i>\n\n"
        "📝 На какой день вы хотите записаться? Выберите дату! <i>(Прием в порядке живой очереди)</i>",
        reply_markup=get_dates_keyboard(),
        parse_mode="HTML",
    )

@dp.callback_query(F.data.startswith("book_date_"))
async def process_date_selection(callback: types.CallbackQuery, state: FSMContext):
    selected_date = callback.data.split("book_date_")[1]
    await state.update_data(selected_date=selected_date)
    await state.set_state(BookingState.waiting_for_phone)
    
    await callback.message.answer(
        "📞 <b>Iltimos, shifokor siz bilan bogʻlanishi uchun telefon raqamingizni yuboring!</b>\n"
        "Pastdagi '📱 Raqamni yuborish' tugmasini bosing yoki raqamingizni yozib yuboring.\n\n"
        "📞 <b>Пожалуйста, отправьте ваш номер телефона для связи!</b>\n"
        "Нажмите кнопку '📱 Отправить номер' ниже или введите номер вручную.",
        reply_markup=get_phone_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()

@dp.message(BookingState.waiting_for_phone)
async def process_booking_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    
    if not message.contact and (not phone or len(phone) < 5):
        await message.answer("⚠️ Iltimos, haqiqiy telefon raqamingizni kiriting yoki pastdagi tugmani bosing.")
        return

    user_data = await state.get_data()
    selected_date = user_data.get("selected_date")
    
    user_name = html_decoration.quote(message.from_user.full_name)
    user_link = f"<a href='tg://user?id={message.from_user.id}'>{user_name}</a>"
    
    # Shifokorga xabar yuborish
    doctor_msg = (
        "📥 <b>YANGI QABULGA YOZILISH!</b>\n\n"
        f"👤 <b>Bemor:</b> {user_link}\n"
        f"📱 <b>Tel:</b> {phone}\n"
        f"📅 <b>Sana:</b> {selected_date}\n"
        "ℹ️ <i>Qabul jonli navbat tartibida.</i>"
    )
    await bot.send_message(DOCTOR_CHAT_ID, doctor_msg, parse_mode="HTML")
    
    # Bemorga javob qaytarish
    await message.answer(
        "Qabulga yozildingiz. Belgilangan kuni jonli navbat tartibida kelishingiz mumkin. Kutamiz!\n\n"
        "Вы записались на прием. Вы можете прийти в выбранный день в порядке живой очереди. Ждем вас!",
        reply_markup=get_main_keyboard(),
    )
    await state.clear()

# Uyga chaqiruv jarayoni
@dp.message(F.text == "🏠 Uyga chaqiruv | Вызов на дом")
async def home_visit_start(message: types.Message):
    ikb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha / Да", callback_data="home_yes"),
                InlineKeyboardButton(text="❌ Yoʻq / Нет", callback_data="home_no"),
            ]
        ]
    )
    await message.answer(
        "🏠 Uyga chaqiruv xizmati <b>Toshkent shahri</b> boʻyicha koʻrsatiladi.\n"
        "💵 Chaqiruv narxi: <b>450 000 soʻm</b>.\n"
        "⚠️ <i>Chaqiruv shifokor shaxsan tasdiqlaganidan soʻng kuchga kiradi.</i>\n\n"
        "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        "🏠 Услуга вызова на дом оказывается по <b>городу Ташкент</b>.\n"
        "💵 Стоимость вызова: <b>450 000 сум</b>.\n"
        "⚠️ <i>Вызов подтверждается только после личного согласия врача.</i>",
        reply_markup=ikb,
        parse_mode="HTML",
    )

@dp.callback_query(F.data == "home_no")
async def home_visit_cancel(callback: types.CallbackQuery):
    await callback.message.answer(
        "Botimizdan foydalanganingiz uchun rahmat! Salomat boʻling! 😊\n\n"
        "Спасибо за использование нашего бота! Будьте здоровы! 😊",
        reply_markup=get_main_keyboard(),
    )
    await callback.answer()

@dp.callback_query(F.data == "home_yes")
async def home_visit_confirm(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(HomeVisitState.waiting_for_location)
    await callback.message.answer(
        "📍 Iltimos, joylashgan manzilingizni (geolokatsiyangizni) yuboring!\n\n"
        "📍 Пожалуйста, отправьте вашу геолокацию!",
        reply_markup=get_location_keyboard(),
    )
    await callback.answer()

@dp.message(HomeVisitState.waiting_for_location)
async def process_home_location(message: types.Message, state: FSMContext):
    if not message.location:
        await message.answer("Iltimos, pastdagi '📍 Lokatsiyani yuborish' tugmasini bosing.")
        return
        
    await state.update_data(lat=message.location.latitude, lon=message.location.longitude)
    await state.set_state(HomeVisitState.waiting_for_phone)
    
    await message.answer(
        "📞 Endi shifokor siz bilan bogʻlanishi uchun telefon raqamingizni yuboring!\n\n"
        "📞 Теперь отправьте ваш номер телефона для связи!",
        reply_markup=get_phone_keyboard(),
    )

@dp.message(HomeVisitState.waiting_for_phone)
async def process_home_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    
    if not message.contact and (not phone or len(phone) < 5):
        await message.answer("⚠️ Iltimos, haqiqiy telefon raqamingizni kiriting yoki pastdagi tugmani bosing.")
        return

    user_data = await state.get_data()
    
    patient_id = message.from_user.id
    user_name = html_decoration.quote(message.from_user.full_name)
    user_link = f"<a href='tg://user?id={patient_id}'>{user_name}</a>"
    
    # Shifokorga geolokatsiyani yuborish
    await bot.send_location(
        DOCTOR_CHAT_ID,
        latitude=user_data["lat"],
        longitude=user_data["lon"]
    )
    
    # Shifokorga chaqiruv ma'lumotlarini va tasdiqlash tugmasini yuborish
    confirm_ikb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Chaqiruvni tasdiqlash", callback_data=f"confirm_visit_{patient_id}")]
        ]
    )
    
    doctor_msg = (
        "🚨 <b>YANGI UYGA CHAQIRUV!</b>\n\n"
        f"👤 <b>Bemor:</b> {user_link}\n"
        f"📱 <b>Tel:</b> {phone}\n"
        "📍 <b>Geolokatsiya:</b> tepada yuborildi."
    )
    await bot.send_message(DOCTOR_CHAT_ID, doctor_msg, reply_markup=confirm_ikb, parse_mode="HTML")
    
    await message.answer(
        "✅ Maʼlumotlaringiz qabul qilindi. Shifokor chaqiruvni koʻrib chiqib, tez orada tasdiq xabarini yuboradi!\n\n"
        "✅ Ваши данные приняты. Врач рассмотрит вызов и вскоре отправит подтверждение!",
        reply_markup=get_main_keyboard(),
    )
    await state.clear()

# Shifokor tomonidan tasdiqlash mantiqi
@dp.callback_query(F.data.startswith("confirm_visit_"))
async def doctor_start_confirmation(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != DOCTOR_CHAT_ID:
        return
    patient_id = int(callback.data.split("confirm_visit_")[1])
    await state.update_data(patient_id=patient_id)
    await state.set_state(DoctorConfirmState.waiting_for_time_input)
    
    await callback.message.answer(
        "✍️ Bemorga qaysi kuni va soat nechada bora olishingizni yozib yuboring.\n"
        "*(Masalan: Bugun soat 19:30 da boraman)*"
    )
    await callback.answer()

@dp.message(DoctorConfirmState.waiting_for_time_input)
async def doctor_send_confirmation(message: types.Message, state: FSMContext):
    if message.from_user.id != DOCTOR_CHAT_ID:
        return
    data = await state.get_data()
    patient_id = data.get("patient_id")
    doctor_text = message.text
    
    patient_msg = (
        "✅ <b>Shifokor chaqiruvni tasdiqladi!</b>\n"
        f"👨‍⚕️ <b>Shifokor xabari:</b> {doctor_text}\n\n"
        "✅ <b>Врач подтвердил вызов!</b>\n"
        f"👨‍⚕️ <b>Сообщение от врача:</b> {doctor_text}"
    )
    
    try:
        await bot.send_message(patient_id, patient_msg, parse_mode="HTML")
        await message.answer("✅ Bemorga tasdiq xabari muvaffaqiyatli yuborildi!")
    except Exception as e:
        await message.answer(f"❌ Xabar yuborishda xatolik yuz berdi: {e}")
        
    await state.clear()

# Asosiy ishga tushirish funksiyasi
async def main():
    print("Bot muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import threading
    
    def run_web():
        web.run_app(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

    # Veb-serverni alohida oqimda ishga tushiramiz
    t = threading.Thread(target=run_web, daemon=True)
    
    # Asosiy oqimda bot ishlayveradi
    asyncio.run(main())
