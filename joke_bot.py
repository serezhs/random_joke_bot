import logging
import os
import re

import requests
import telebot
from dotenv import load_dotenv
from telebot import types

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.ERROR, filename='bot_logs.log', filemode='w')

load_dotenv()
bot_token = os.getenv('TOKEN')
server_url = os.getenv('URL')

bot = telebot.TeleBot(bot_token)  # API-токен бота в телеграм
URL = server_url  # домен на котором располагается апи проекта

last_message = {}
mass_adding_users = []


# инструкция по пользованию ботом
@bot.message_handler(commands=['start'])
def instruction(message):
    # добавление кнопок
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    sent_joke = types.KeyboardButton('скинь анек')
    adding_jokes = types.KeyboardButton('массовое добавление анекдотов')
    help = types.KeyboardButton('инструкция')
    markup.add(sent_joke)
    markup.add(adding_jokes, help)

    instruction = (
        f'Привет, {message.chat.first_name}! Это бот для обмена анекдотами.'
        '\n\n'
        '• Нажав кнопку <i><b>скинь анек</b></i> '
        'ты получишь случайный анекдот '
        'из базы, которая составляется всеми пользователями проекта.\n'
        'Под анекдотом будет его рейтинг и имя человека, добавившего анкдот. '
        'Кнопками 👍/👎 ты можешь изменить рейтинг анекдота.\n'
        '<u>Анекдоты с рейтингом меньше <b>-10</b> автоматически удаляются</u>'
        '\n\n'
        '• Чтобы добавить свой анекдот просто отправь его боту. '
        '<u><b>Будь внимателен: </b></u>'
        '<b>Таким образом можно добавлять анекдоты только по одному.</b>'
        '\n\n'
        'Если ты хочешь загрузить сразу несколько анекдотов - '
        'нажми кнопку <i><b>массовое добавление анекдотов</b>.</i> '
        'Каждое сообщение будет добавлено в базу как отдельный анекдот.\n'
        'Чтобы вернуться в основное меню нажми: '
        '<i><b>❌выйти из режима массового добавления❌</b></i>'
        '\n\n'
        '• По кнопке <i><b>инструкция</b></i> ты всегда можешь '
        'ознакомиться с актуальной инструкцией '
        'и изучить описание новых функций, когда они появятся'
        '\n\n'
        'Дополнительная информация доступна в описании бота'
    )

    # отправка сообщения с инструкцией
    bot.send_message(
        message.chat.id, instruction, parse_mode='html', reply_markup=markup
        )


# обработка входящих сообщений и вызов нужных функий
@bot.message_handler(content_types=['text'])
def message_processing(message):
    if message.text == 'скинь анек':
        send_random_joke(message)
    elif message.text == 'инструкция':
        instruction(message)
    elif message.text == 'массовое добавление анекдотов':
        adding_jokes(message)
    elif message.text == '❌выйти из режима массового добавления❌':
        mass_adding_exit(message)
    else:
        get_random_joke(message)


# получение случайной шутки
def send_random_joke(message):
    try:
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
        bot.send_message(
            message.chat.id, text, parse_mode='html',
            reply_markup=markup
            )

    # если произошла ошибка
    except Exception as error:
        # добавления записи об ошибки в файл логов
        logging.error(
            f'Ошибка при отправке случайной шутки пользователю: {error}'
            )


# добавление шутки
def get_random_joke(message):
    global mass_adding_users

    # проверка, включен ли режим массового добавления
    if message.chat.id in mass_adding_users:
        try:
            # сбор данных для post запроса
            text = message.text
            name = ''
            surname = ''
            if message.chat.first_name:
                name = message.chat.first_name
            if message.chat.last_name:
                surname = message.chat.last_name
            author = name + ' ' + surname
            data = {
                "text": text,
                "author": author
                }

            # отправка оценки на сервер
            request = requests.post(URL + 'jokes/', data=data)
            request = request.json()

            # составление сообщения пользователю
            joke_number = request['id']
            text = f'анекдот №{joke_number} добавлен😎👍'

            # отправка сообщения, что шутка создана
            bot.send_message(message.chat.id, text)

        # если произошла ошибка
        except Exception as error:
            # добавления записи об ошибки в файл логов
            logging.error(
                'Ошибка при получении случайной шутки '
                f'от пользователя в режиме массового добавления: {error}'
                )
            # отправка сообщения, что шутка не добавлена
            bot.send_message(
                    message.chat.id,
                    'Не удалось добавить анекдот: сервер не отвечает🥲'
                    )

    # если режим массового добавления не включен -
    # дополнительно запрашивать подтверждение
    else:
        # вывод кнопок да/нет
        markup = types.InlineKeyboardMarkup()
        yes = types.InlineKeyboardButton('да✅', callback_data='yes')
        no = types.InlineKeyboardButton('нет❌', callback_data='no')
        markup.add(yes, no)

        # временное сохранение сообщения
        global last_message
        last_message[message.chat.id] = message.text

        # запрос подтверждения
        bot.send_message(
            message.chat.id,
            'Вы уверены, что хотите добавить этот анекдот?',
            reply_markup=markup
            )


# режим массового добавления шуток
def adding_jokes(message):
    # вывод кнопоки входа из режима массового добавления
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    exit = types.KeyboardButton('❌выйти из режима массового добавления❌')
    markup.add(exit)

    # включение режима массового добавления
    global mass_adding_users
    if message.chat.id not in mass_adding_users:
        mass_adding_users.append(message.chat.id)

    # подготовка текста сообщения
    text = 'теперь можно добавлять анекдоты без дополнительного подтверждения'

    # отправка сообщения пользователю
    bot.send_message(message.chat.id, text, reply_markup=markup)


# отключение режима массового добавления
def mass_adding_exit(message):
    # отключение режима
    global mass_adding_users
    if message.chat.id in mass_adding_users:
        mass_adding_users.remove(message.chat.id)

    # возврат кнопок
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    sent_joke = types.KeyboardButton('скинь анек')
    adding_jokes = types.KeyboardButton('массовое добавление анекдотов')
    help = types.KeyboardButton('инструкция')
    markup.add(sent_joke)
    markup.add(adding_jokes, help)

    bot.send_message(
        message.chat.id, 'режим массового добавления отключен',
        reply_markup=markup
        )


# обработка кнопок, прикрепленных к сообщению
@bot.callback_query_handler(func=lambda call: True)
def get_reply(call):
    # обработка кнопки лайк анекдоту
    if call.data == 'like':
        try:
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

            # создание кнопки ✅
            markup = types.InlineKeyboardMarkup()
            ok = types.InlineKeyboardButton('✅', callback_data='ok')
            markup.add(ok)

            # вывод кнопки ✅ вместо кнопок оценки
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id, message_id=call.message.id,
                reply_markup=markup
                )

            # сообщение пользователю
            bot.answer_callback_query(call.id, 'ваш голос очень важен для нас')

        # если произошла ошибка
        except Exception as error:
            # добавления записи об ошибки в файл логов
            logging.error(
                'Ошибка при получении оценки '
                f'от пользователя: {error}'
                )

            # создание кнопки 😵‍💫
            markup = types.InlineKeyboardMarkup()
            ok = types.InlineKeyboardButton('😵‍💫', callback_data='error')
            markup.add(ok)

            # замена кнопок с оценками кнопкой 😵‍💫
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id, message_id=call.message.id,
                reply_markup=markup
                )

            # отправка сообщения, что оценка не учтена
            bot.send_message(
                    call.message.chat.id,
                    'Не удалось добавить оценку: сервер не отвечает🥲'
                    )

    # обработка кнопки дизлайк к анекдоту
    if call.data == 'dislike':
        try:
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

            # создание кнопки ✅
            markup = types.InlineKeyboardMarkup()
            ok = types.InlineKeyboardButton('✅', callback_data='ok')
            markup.add(ok)

            # вывод кнопки ✅ вместо кнопок оценки
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id, message_id=call.message.id,
                reply_markup=markup
                )

            # сообщение пользователю
            bot.answer_callback_query(call.id, 'ваш голос очень важен для нас')

        # если произошла ошибка
        except Exception as error:
            # добавления записи об ошибки в файл логов
            logging.error(
                'Ошибка при получении оценки '
                f'от пользователя: {error}'
                )

            # создание кнопки 😵‍💫
            markup = types.InlineKeyboardMarkup()
            ok = types.InlineKeyboardButton('😵‍💫', callback_data='error')
            markup.add(ok)

            # замена кнопок с оценками кнопкой 😵‍💫
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id, message_id=call.message.id,
                reply_markup=markup
                )

            # отправка сообщения, что оценка не учтена
            bot.send_message(
                    call.message.chat.id,
                    'Не удалось добавить оценку: сервер не отвечает🥲'
                    )

    # обработка кнопки да при принятии анекдота от пользователя
    if call.data == 'yes':
        try:
            # сбор данных для post запроса
            global last_message
            text = last_message[call.message.chat.id]
            del last_message[call.message.chat.id]
            name = ''
            surname = ''
            if call.message.chat.first_name:
                name = call.message.chat.first_name
            if call.message.chat.last_name:
                surname = call.message.chat.last_name
            author = name + ' ' + surname
            data = {
                "text": text,
                "author": author
                }

            # отправка оценки на сервер
            request = requests.post(URL + 'jokes/', data=data)
            request = request.json()

            # удаление кнопок
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id, message_id=call.message.id,
                reply_markup=None
                )

            # составление сообщения пользователю
            joke_number = request['id']
            text = f'анекдот №{joke_number} добавлен😎👍'

            # отправка сообщения, что шутка создана
            bot.send_message(call.message.chat.id, text)

        # если произошла ошибка
        except Exception as error:
            # добавления записи об ошибки в файл логов
            logging.error(
                'Ошибка при получении случайной шутки '
                f'от пользователя: {error}'
                )

            # создание кнопки 😵‍💫
            markup = types.InlineKeyboardMarkup()
            ok = types.InlineKeyboardButton('😵‍💫', callback_data='error')
            markup.add(ok)

            # замена кнопок с оценками кнопкой 😵‍💫
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id, message_id=call.message.id,
                reply_markup=markup
                )

            # отправка сообщения, что шутка не добавлена
            bot.send_message(
                    call.message.chat.id,
                    'Не удалось добавить анекдот: сервер не отвечает🥲'
                    )

    # обработка кнопки да при принятии анекдота от пользователя
    if call.data == 'no':
        # удаление кнопок
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id, message_id=call.message.id,
            reply_markup=None
            )

        # отправка сообщения
        bot.send_message(call.message.chat.id, 'ну нет так нет¯|_(ツ)_/¯')

    # обработка кнопки ✅, которая выводится после оценки
    if call.data == 'ok':
        bot.answer_callback_query(call.id, 'оценка учтена')

    # обработка кнопки 😵‍💫, которая выводится в случае ошибки
    if call.data == 'error':
        bot.answer_callback_query(call.id, 'что-то пошло не так')


def main():
    # строка чтоб бот принимал сообщения
    bot.polling(non_stop=True)


if __name__ == '__main__':
    main()
