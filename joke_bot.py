import re

import requests
import telebot
from telebot import types

bot = telebot.TeleBot('*')
URL = 'http://127.0.0.1:8000/'  # домен на котором располагается апи проекта


# инструкция по пользованию ботом
@bot.message_handler(commands=['start', 'help'])
def instruction(message):
    # добавление кнопок
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    sent_joke = types.KeyboardButton('скинь анек')
    adding_jokes = types.KeyboardButton('добавить свои анекдоты')
    help = types.KeyboardButton('инструкция')
    markup.add(sent_joke)
    markup.add(adding_jokes, help)

    # отправка сообщения с инструкцией
    bot.send_message(message.chat.id, '!!!инструкция!!!', parse_mode='html',
                     reply_markup=markup)


# для меня чтоб смотреть как вытянуть id, имя и др
# потом удалить
@bot.message_handler(commands=['info'])
def info(message):
    bot.send_message(message.chat.id, message)


# обработка входящих сообщений и вызов нужных функий
@bot.message_handler(content_types=['text'])
def message_processing(message):
    if message.text == 'скинь анек':
        send_random_joke(message)
    elif message.text == 'инструкция':
        instruction(message)
    elif message.text == 'добавить свои анекдоты':
        adding_jokes(message)
    else:
        get_random_joke(message)


# получение случайной шутки
def send_random_joke(message):
    # вывод кнопок like&dislike
    markup = types.InlineKeyboardMarkup()
    like = types.InlineKeyboardButton('👍', callback_data='like')
    dislike = types.InlineKeyboardButton('👎', callback_data='dislike')
    markup.add(like, dislike)

    # запрос шутки с сервера
    response = requests.get(URL + 'jokes/')
    response = response.json()
    joke = response['text']
    joke_id = response['id']
    joke_rating = response['rating']
    joke_author = response['author']

    # составление текста шутки
    text = (
        f'анекдот № {joke_id}\n\n{joke}\n\n'
        f'рейтинг: {joke_rating}\n{joke_author}'
        )

    # отправка шутки
    bot.send_message(message.chat.id, text, parse_mode='html',
                     reply_markup=markup)


# добавление одной шутки
def get_random_joke(message):
    # вывод кнопок да/нет
    markup = types.InlineKeyboardMarkup()
    yes = types.InlineKeyboardButton('да✅', url='google.com')
    no = types.InlineKeyboardButton('нет❌', url='google.com')
    markup.add(yes, no)

    # запрос подтверждения
    bot.send_message(
        message.chat.id,
        'Вы уверены, что хотите добавить этот анекдот?',
        reply_markup=markup
        )


# режим массового добавления шуток
def adding_jokes(message):
    pass


# обработка кнопок, прикрепленных к сообщению
@bot.callback_query_handler(func=lambda call: True)
def get_like(call):
    # обработка кнопки лайк анекдоту
    if call.data == 'like':
        # сбор данных для post запроса
        user_id = call.message.chat.id
        text = call.message.text
        id = re.search(r'\d+', text)
        joke_id = int(id[0])
        data = {
            "mark": 1,
            "user": user_id,
            "joke": joke_id
            }

        # отправка оценки на сервер
        requests.post(URL + 'vote/', data=data)

        # # вывод кнопки ✅ вместо кнопок оценки
        # markup = types.InlineKeyboardMarkup()
        # ok = types.InlineKeyboardButton('✅', callback_data='dislike')
        # markup.add(ok)

        # сообщение пользователю
        bot.answer_callback_query(call.id, 'оценка учтена')

    # обработка кнопки дизлайк к анекдоту
    if call.data == 'dislike':
        # сбор данных для post запроса
        user_id = call.message.chat.id
        text = call.message.text
        id = re.search(r'\d+', text)
        joke_id = int(id[0])
        data = {
            "mark": -1,
            "user": user_id,
            "joke": joke_id
            }

        # отправка оценки на сервер
        requests.post(URL + 'vote/', data=data)

        # # вывод кнопки ✅ вместо кнопок оценки
        # markup = types.InlineKeyboardMarkup()
        # ok = types.InlineKeyboardButton('✅', callback_data='dislike')
        # markup.add(ok)

        # сообщение пользователю
        bot.answer_callback_query(call.id, 'оценка учтена')


# строка чтоб бот принимал сообщения
bot.polling(non_stop=True)
