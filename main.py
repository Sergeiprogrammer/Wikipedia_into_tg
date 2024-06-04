import telebot
import wikipedia

API_TOKEN = 'your api token'

bot = telebot.TeleBot(API_TOKEN)

#
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "привет это бот для поиска информации обратитесь к команде /help если в первый раз зашли")

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, "список команд /search - поиск , login - для изменений своего аккаунта (вы атоматическии входитев систему при каждом заупске бота)")

@bot.message_handler(commands=['search'])
def search(message):
    lang = "ru" # получегние языка из дб
    wikipedia.set_lang(lang)
    bot.reply_to(message,"введите информацю для поиска")
    bot.register_next_step_handler(message, search_step_2)

def search_step_2(message):
    user_input = message.text
    article = wikipedia.search(user_input)
    for i in article:
        bot.reply_to(message, i)
    bot.reply_to(message, "скопируйте названии статьи из списка или напшите что то другое")
    bot.register_next_step_handler(message, process_article)

def process_article(message,len_mes):
    try:
        len_mes = "1"  # поулчении интрересов по длине статьи 1/2
        user_input = message.text
        if len_mes == "1":
            article = wikipedia.page(user_input)
            bot.reply_to(message, article.content)
        elif len_mes == "2":
            article = wikipedia.summary(user_input)
            bot.reply_to(message, article.content)
    except:
        bot.reply_to(message, "не опридилилась статья")

@bot.message_handler(commands=["login"])
def log(message):
    bot.reply_to(message, 'для качетсво сервиса мы зададим вам впросы 1:')
    all_lang = [wikipedia.languages()]
    bot.reply_to(message, "введите язык")
    bot.register_next_step_handler(message, process_lang, all_lang)

def process_lang(message,all_lang):
    user_lang = message.text
    if user_lang not in all_lang:
        bot.reply_to(message, "вашего языка нет здесь")
        bot.reply_to(message, all_lang)
    else:
        bot.reply_to(message, "идём дальше")
        bot.reply_to(message, "на сколько длинными вы хотите видеть статьи: 1полная или 2 краткая введите номер")
        bot.register_next_step_handler(message, process_len)

def process_len(message):
    user_len = message.text
    if user_len == "2":
        bot.reply_to(message, "ок будет короткая ")
        # добавление в базу
    elif user_len == "1":
        bot.reply_to(message, "ок будет полная ")
        #добавление в базу
    else:
        bot.reply_to(message, "ошибка номер не равен 1 или 2")

bot.infinity_polling()
