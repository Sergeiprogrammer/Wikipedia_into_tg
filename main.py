import telebot  # Импортируем библиотеку telebot для работы с Telegram API
from telebot import types #красивы кнопочки :)
import pyttsx3 #аудио конвертор статей
import wikipedia  # Импортируем библиотеку wikipedia для работы с Википедией
import sqlite3 # загрузка базы данных
from g4f.client import Client #нейросеть
from googletrans import Translator # переводчик для нейросети для лучшего качетсва ответа

# Соединяемся с базой данных
conn = sqlite3.connect('main.db')

# Создаем курсор
c = conn.cursor()

# Создаем таблицу
c.execute('''
CREATE TABLE IF NOT EXISTS user_db (
    user_id INTEGER,
    len TEXT ,
    lang TEXT
)
''')
# таблица люимых статей
c.execute('''
CREATE TABLE IF NOT EXISTS favorite (
    user_id INTEGER,
    favorite_article TEXT
)
''')

API_TOKEN = 'token'  # Замените 'api' на ваш реальный API токен

bot = telebot.TeleBot(API_TOKEN)  # Создаем объект бота

@bot.message_handler(commands=["ai_search"])
def ai_help(message):
    bot.reply_to(message, "Вас приветствует ИИ! Опишите, про что была статья")
    bot.register_next_step_handler(message,ai_search)
def ai_search(message):
    ask = message.text
    translator = Translator()
    translation = translator.translate(ask, dest='en')
    ask = translation.text
    bot.reply_to(message,"подождите бот думает")
    client = Client()
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": f"hi find article on wikipedia about {ask}"}],
    )
    user_input = translator.translate(response.choices[0].message.content, dest='ru').text
    if "Извините, ваш IP был запрещен " in user_input:
        bot.reply_to(message,"ошибка нейросети")
    else:
        bot.reply_to(message, user_input)


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Это бот для поиска информации. Обратитесь к команде /help, если вы здесь впервые.")

# Обработчик команды /help
@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, "Список команд:\n/search - поиск\n/login - для изменения своего аккаунта\n/help - для вывода всех команд\n/favorite любимые статьи\n/ai_search поиск с помщью ИИ \n/audio_seacrh преобразует стати в аудио")

# Обработчик команды /search
@bot.message_handler(commands=['search'])
def search(message):
    conn = sqlite3.connect('main.db')  # новый конект к базе
    c = conn.cursor()
    user_id = str(message.from_user.id) #получаем id
    c.execute(f"SELECT * FROM user_db WHERE user_id = {user_id}")
    if c.fetchone():  # проверка есть ли информация в базе
        c.execute(f"SELECT lang FROM user_db WHERE user_id = {user_id}")
        lang = c.fetchone()[0]
        c.close()
        if lang:  # проверяем наличие языка
            wikipedia.set_lang(lang)  # Устанавливаем язык для Wikipedia API
        else: # ставим английский он дефотный
            wikipedia.set_lang('en')  # default language
        bot.reply_to(message, "Введите информацию для поиска")  # запрашиваем информацию для поиска
        bot.register_next_step_handler(message, search_step_2)  # Переходим к следующему шагу поиска
    else:  # елси нет то предлагает добваить в db
        bot.reply_to(message, "запустите функцию /login")

# Следующий шаг поиска
def search_step_2(message):
    user_input = message.text  # Получаем текст сообщения от пользователя
    article = wikipedia.search(user_input)  # Ищем статьи в Википедии по введенному запросу
    for i in article: # переберает все статьии
        bot.reply_to(message, i)  # Отправляем список найденных статей
    bot.reply_to(message, "Скопируйте название статьи из списка или напишите что-то другое") #отправка сообщений
    bot.register_next_step_handler(message, process_article)  # Переходим к следующему шагу обработки статьи

# Обработка выбранной статьи
def process_article(message):
    conn = sqlite3.connect('main.db')  # новый конект к базе
    c = conn.cursor()
    user_id = message.from_user.id
    c.execute(f"SELECT len FROM user_db WHERE user_id = {user_id}")
    len_mes = c.fetchone()[0]  # Получение предпочтений по длине статьи (1 - полная, 2 - краткая)
    c.close()
    try:
        user_input = message.text  # Получаем текст сообщения от пользователя
        bot.reply_to(message, "подожидте чуть чуть!")
        if len_mes == "1": # если длинна = 1 будет полна статья
            article = wikipedia.page(user_input)  # Получаем полную статью
            value = 4096
            start = 0
            max = len(article.content)
            if max > 4096:
                for i in range(max // 4096): # из за ограничения 4096 сиволов делим её на чати
                    short_content = article.content[start:value]
                    title = article.title
                    bot.reply_to(message, short_content)
                    start += 4096
                    value += 4096
                # Send the remaining content as a separate message
                remaining_content = article.content[start:max] # выводим то что не взлезло
                if remaining_content:
                    bot.reply_to(message, remaining_content)
            else:
                bot.reply_to(message, article.content)
        elif len_mes == "2": # если длинна = 2 будет краткая статья
            article = wikipedia.summary(user_input)  # Получаем краткое содержание статьи
            bot.reply_to(message, article.content)  # Отправляем краткое содержание пользователю
        bot.reply_to(message, "хотите добавть её в любимые?")
        markup = types.ReplyKeyboardMarkup() # создаем кнопки
        btn1 = types.KeyboardButton('да')
        btn2 = types.KeyboardButton('нет')
        markup.row(btn1, btn2)
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)
        title = wikipedia.page(user_input).title

        bot.register_next_step_handler(message, favorite_varificate, title)

    except Exception as e:  # Обработка исключений
        bot.reply_to(message, f"Не удалось найти статью")  # Сообщаем пользователю об ошибке

def favorite_varificate(message,title): # проверка хочет ли человека добавить в любимые
    if message.text == "да":
        user_id = message.from_user.id
        conn = sqlite3.connect('main.db')  # новый конект к базе
        c = conn.cursor()
        c.execute(
            f"INSERT INTO favorite (user_id,favorite_article) VALUES  ({user_id},'{title}')")  # добовляет любимую статью
        conn.commit()
        c.close() # отключает конект
        bot.reply_to(message,"операция выполнена успешно")
    elif message.text == "нет":
        bot.reply_to(message, "ок")
    else:
        bot.reply_to(message, "команда не опознана")
    markup = types.ReplyKeyboardRemove() # убираем кнопки

# Обработчик команды /login
@bot.message_handler(commands=["login"])
def log(message):
    bot.reply_to(message, 'Для улучшения качества сервиса мы зададим вам несколько вопросов.')
    all_lang = wikipedia.languages()  # Получаем список доступных языков
    bot.reply_to(message, "Введите язык")
    bot.register_next_step_handler(message, process_lang, all_lang)  # Переходим к следующему шагу обработки языка

# Обработка введенного языка
def process_lang(message, all_lang):
    user_lang = message.text  # Получаем текст сообщения от пользователя
    if user_lang not in all_lang:  # Проверяем, существует ли введенный язык
        bot.reply_to(message, "Вашего языка нет в списке")
        bot.reply_to(message, str(all_lang))  # Отправляем список доступных языков
    else: #елси не существует то выполняем это
        bot.reply_to(message, "Идем дальше.")
        bot.reply_to(message, "На сколько длинной будет статья: 1 - полная или 2 - краткая? Введите номер.")
        bot.register_next_step_handler(message, process_len,user_lang)  # Переходим к следующему шагу обработки длины статьи

# Обработка введенной длины стать
def process_len(message, user_lang):
    conn = sqlite3.connect('main.db')  # новый конект к базе
    c = conn.cursor()
    user_len = message.text
    user_id = message.from_user.id
    if user_len in ["1", "2"]: #проверяте ввод человека
        c.execute(f"INSERT INTO user_db (user_id,len,lang) VALUES ({user_id},{user_len},'{user_lang}')") #добавляет всё в базу данных
        conn.commit()
        c.close()
        bot.reply_to(message, "Настройки сохранены. нажимет /help для списка комманд ")
    else:
        bot.reply_to(message, "Ошибка. Попробуйте еще раз.")

@bot.message_handler(commands=['favorite'])
def favorite(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('main.db')  # новый конект к базе
    c = conn.cursor()
    c.execute(f"SELECT favorite_article FROM favorite WHERE user_id = {user_id}") #вывод всех статей
    bot.reply_to(message, f"вот список статей: {c.fetchall()} ")
    c.close()
    bot.reply_to(message, "хотите удалить любимую статью?")
    markup = types.ReplyKeyboardMarkup()
    btn1 = types.KeyboardButton('да') # создаем кнопки
    btn2 = types.KeyboardButton('нет')
    markup.row(btn1, btn2)
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)
    bot.register_next_step_handler(message,favorite_question)

def favorite_question(message): # рисует кнопки и предлагает удалить статьи
    if message.text == "да":
        bot.reply_to(message,"ок")
        bot.reply_to(message, "введите название")
        bot.register_next_step_handler(message, remove_favorite)
    elif message.text == "нет":
        bot.reply_to(message,"ок")
    else:
        bot.reply_to(message, "команда не опознана!")
    markup = types.ReplyKeyboardRemove() # убираем их

def remove_favorite(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('main.db')  # новый конект к базе
    c = conn.cursor()
    user_input = message.text
    c.execute('DELETE FROM favorite WHERE user_id =? AND favorite_article =?', (user_id, user_input))
    conn.commit()
    c.close()
    bot.reply_to(message, "операция прошла успешно")


@bot.message_handler(commands=['audio_seacrh'])
def search_article(message):
    bot.reply_to(message,"введите название статьий")
    bot.register_next_step_handler(message, audio_create)

def audio_create(message):
    user_id = message.from_user.id
    article = wikipedia.page(message.text)  # Получаем полную статью
    bot.reply_to(message,f"внимание преобразовани {article.title} в аудио может занять время можите заняться своими делами!")
    start = 0
    value = 16384
    max = len(article.content)
    if max > 4096:
        for i in range(max // 16384):  # из за ограничения 4096 сиволов делим её на чати
            short_content = article.content[start:value]
            if len(short_content) <= max - len(short_content):
                start += 4096
                value += 4096
                engine = pyttsx3.init()
                engine.save_to_file(short_content, f"D:\\windos_custom\\codland\\audios\\{user_id}.mp3")
                engine.runAndWait()
                engine.stop()
                with open(f'D:\\windos_custom\\codland\\audios\\{user_id}.mp3', 'rb') as audio:
                    bot.send_audio(message.chat.id, audio)
            else:
                remaining_content = article.content[start:max]  # выводим то что не взлезло
                engine = pyttsx3.init()
                engine.save_to_file(article.content, f"D:\\windos_custom\\codland\\audios\\{user_id}.mp3")
                engine.runAndWait()
                engine.stop()
                with open(f'D:\\windos_custom\\codland\\audios\\{user_id}.mp3', 'rb') as audio:
                    bot.send_audio(message.chat.id, audio)
        # Send the remaining content as a separate message





bot.infinity_polling()  # Запуск бесконечного цикла для обработки сообщений
