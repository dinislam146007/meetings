"""Основной файл бота"""
import datetime
import threading
import time
import math
import threading

import telebot
from keyboa import Keyboa, Button

from database import open_connection
import smtplib
from email.mime.text import MIMEText


bot = telebot.TeleBot('', parse_mode='html')

def send_notification_to_assistant(event_name):
    """Отправить уведомление ассистенту о присоединении руководителя к звонку"""
    with open_connection() as connection, connection.cursor(buffered=True) as cursor:
        cursor.execute(
            '''
            SELECT userid FROM users WHERE userrole = %s
            ''',
            ('assist',)
        )
        assistants = cursor.fetchall()
        for assistant in assistants:
            try:
                bot.send_message(assistant[0], f'Руководитель присоединился к звонку "{event_name}"')
            except telebot.apihelper.ApiTelegramException:
                continue

@bot.message_handler(commands=['start_abcdefg'])
def add_person_to_owners(message):
    """Добавить пользователя к владельцам бота"""
    with open_connection() as connection, connection.cursor(buffered=True) as cursor:
        cursor.execute(
            '''
            SELECT id FROM users WHERE userid = %s
            ''',
            (message.chat.id,)
        )
        user = cursor.fetchone()
        if user:
            bot.send_message(message.chat.id, 'Вы уже добавлены в список рассылки.')
            return
        cursor.execute(
            '''
            INSERT INTO users(userid, userrole)
            VALUES (%s, %s)
            ''',
            (message.chat.id, 'owner')
        )
    bot.send_message(message.chat.id, 'Вы добавлены в список рассылки!')


def send_notification(event_id, notification_type='ten_minutes'):
    """Отправить десятиминутное уведомление"""
    with open_connection() as connection, connectionnotification_type.cursor(buffered=True) as cursor:
        cursor.execute(
            '''
            SELECT * FROM users WHERE userrole = %s OR userrole = %s
            ''',
            ('owner', 'assist')
        )
        owners = cursor.fetchall()
        cursor.execute(
            '''
            SELECT * FROM notifications WHERE event_id = %s
            ''',
            (event_id,)
        )
        event = cursor.fetchall()
    if not event:
        return
    event = event[0]
    keyboard = Keyboa(items=[Button(
        button_data={'Захожу': f'close_message&{event[0]}'}).button
                             ]).keyboard
    messages = []
    if notification_type == 'ten_minutes':
        if event[5]:
            return
        for owner in owners:
            try:
                bot.send_message(owner[1], f'<b>{event[1]}</b>\n\n'
                                           f'Мит состоится через 10 минут.\n'
                                           f'<i>Нажмите кнопку ниже, чтобы присоединится.</i>',
                                 reply_markup=keyboard)
                with open_connection() as connection, connection.cursor(buffered=True) as cursor:
                    cursor.execute(
                            '''
                            UPDATE notifications SET ten_minutes_sent = %s WHERE event_id = %s
                            ''',
                            (1, event_id)
                        )
            except telebot.apihelper.ApiTelegramException:
                continue
    elif notification_type == 'five_minutes':
        if event[6]:
            return
        subject = f"Звонок {event[1]} через пять минут"
        body = f"Звонок {event[1]} через пять минут. Ссылка: {event[3]}"
        msg = MIMEText(body, 'plain')
        msg['Subject'] = subject
        msg['From'] = ''
        msg['To'] = ''
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login('mail', 'password')
        server.send_message(msg)
        server.quit()

        with open_connection() as connection, connection.cursor(buffered=True) as cursor:
            cursor.execute(
                '''
                UPDATE notifications SET five_minutes_sent = %s WHERE event_id = %s
                ''',
                (1, event_id)
            )
    else:
        for owner in owners:
            try:
                bot.send_message(owner[1], f'<b>{event[1]}</b>\n\n'
                                           f'Мит состоится через один час.\n')
            except telebot.apihelper.ApiTelegramException:
                continue

    with open_connection() as connection, connection.cursor(buffered=True) as cursor:
        for message in messages:
            cursor.execute(
                '''
                INSERT INTO sent_messages(local_event_id, userid, message_id)
                VALUES (%s, %s, %s)
                ''',
                (event[0], message['chat_id'], message['message_id'])
            )


def check_if_link_opened(event_id):
    """Проверка было ли прохождение по ссылке"""
    with open_connection() as connection, connection.cursor(buffered=True) as cursor:
        cursor.execute(
            '''
            SELECT link_opened FROM notifications WHERE event_id = %s
            ''',
            (event_id,)
        )
        link_opened_value = cursor.fetchone()[0]
    if link_opened_value:
        return True
    return False


def delete_message_in_30_seconds(message):
    """Удалить сообщение через 30 секунд"""
    time.sleep(30)
    try:
        bot.delete_message(message.chat.id, message.id)
    except telebot.apihelper.ApiTelegramException:
        pass


@bot.callback_query_handler(func=lambda call: call.data.startswith('close_message&'))
def close_message(call):
    """Закрыть сообщения и отправить уведомление ассистенту"""
    local_event_id = int(call.data.split('&')[1])
    with open_connection() as connection, connection.cursor(buffered=True) as cursor:
        cursor.execute(
            '''
            UPDATE notifications SET link_opened = %s WHERE id = %s
            ''',
            (1, local_event_id)
        )
        cursor.execute(
            '''
            SELECT event_name FROM notifications WHERE id = %s
            ''',
            (local_event_id,)
        )
        event_name = cursor.fetchone()[0]
        cursor.execute(
            '''
            SELECT userid FROM sent_messages WHERE local_event_id = %s AND message_id = %s
            ''',
            (local_event_id, call.message.message_id)
        )
        owner_id = cursor.fetchone()[0]
        send_notification_to_assistant(event_name)  # Отправить уведомление ассистенту
        cursor.execute(
            '''
            DELETE FROM sent_messages WHERE local_event_id = %s AND message_id = %s
            ''',
            (local_event_id, call.message.message_id)
        )
    try:
        bot.delete_message(owner_id, call.message.message_id)
    except telebot.apihelper.ApiTelegramException:
        pass


def start_bot_polling():
    """Функция для запуска бесконечного опроса телеграм бота"""
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except:
            pass
def send_congratulations():
    """Функция для отправки поздравлений руководителям"""
    while True:
        current_time = datetime.datetime.utcnow()
        if current_time.hour == 21 and current_time.minute == 0:
            with open_connection() as connection, connection.cursor(buffered=True) as cursor:
                cursor.execute(
                    '''
                    SELECT userid FROM users WHERE userrole = %s
                    ''',
                    ('owner',)
                )
                owners = cursor.fetchall()
                # Отправляем уведомление каждому руководителю
                for owner in owners:
                    try:
                        bot.send_message(owner[0], f'Сегодня ({current_time.strftime("%d.%m.%Y")}) проект "Название задачи"',
                                         reply_markup=Keyboa(items=[Button('Поздравил', button_data='congratulate')]))
                    except telebot.apihelper.ApiTelegramException:
                        continue
            time.sleep(60)  # Ждем 60 секунд, чтобы не отправлять несколько сообщений за секунду
        else:
            time.sleep(60)

            if datetime.datetime.utcnow().day != current_time.day:
                continue  # Если наступил новый день, перезапускаем цикл

def bot_polling():
    """Обработка запросов бота"""
    while True:
        try:
            bot_thread = threading.Thread(target=start_bot_polling)
            congratulations_thread = threading.Thread(target=send_congratulations)

            bot_thread.start()
            congratulations_thread.start()
        except:
            pass
