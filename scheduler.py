"""Локальное расписание"""
import datetime
import schedule
import time

import bot
from database import open_connection
from bot import send_notification, bot
from google_calendar.calendar_api import GoogleCalendar

def schedule_pending():
    """Проверка расписания"""
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except:
            pass


def update_events():
    """Функция обновления Google Calendar событий"""
    calendars = ['']
    events = []
    for calendar in calendars:
        events += GoogleCalendar().get_events_list(calendar)
    for event in events:
        datetime_start = datetime.datetime.strptime(event['start']['dateTime'].rstrip('Z').split('+')[0],
                                                    '%Y-%m-%dT%H:%M:%S')
        try:
            html_link = event['htmlLink']
            event_name = event['summary']
            event_id = event['id']
        except KeyError:
            continue
        if not event_name.lower().startswith('звонок'):
            continue
        with open_connection() as connection, connection.cursor(buffered=True) as cursor:
            cursor.execute(
                '''
                SELECT id FROM notifications WHERE event_id = %s
                ''',
                (event_id,)
            )
            fetched_event_id = cursor.fetchone()
            if fetched_event_id:
                continue
            cursor.execute(
                '''
                INSERT INTO notifications(name, event_id, html_link, meet_datetime)
                VALUES (%s, %s, %s, %s)
                ''',
                (event_name, event_id, html_link, datetime_start)
            )
        if datetime_start >= datetime.datetime.utcnow():
            schedule_mailing(event_id)


def fill_schedule_after_restart():
    """Заполнение расписания после перезапуска"""
    schedule.clear()
    schedule.every().day.at('00:01').do(fill_schedule_after_restart)
    schedule.every(30).seconds.do(update_events)
    with open_connection() as connection, connection.cursor(buffered=True) as cursor:
        cursor.execute(
            '''
            SELECT * FROM notifications
            WHERE meet_datetime > UTC_TIMESTAMP() AND 
            cast(meet_datetime as date) = UTC_DATE()
            '''
        )
        meets = cursor.fetchall()
    for meet in meets:
        schedule_mailing(meet[2])


def schedule_mailing(event_id):
    """Добавление в расписание отправки сообщения"""
    with open_connection() as connection, connection.cursor(buffered=True) as cursor:
        cursor.execute(
            '''
            SELECT * FROM notifications WHERE event_id = %s
            ''',
            (event_id,)
        )
        event = cursor.fetchone()
    if not event:
        return

    if event[4] <= datetime.datetime.utcnow():
        return

    if event[4].date() != datetime.datetime.utcnow().date():
        return

    with open_connection() as connection, connection.cursor(buffered=True) as cursor:
        cursor.execute(
            '''
            SELECT * FROM users WHERE userrole = %s OR userrole = %s
            ''',
            ('owner', 'assist')
        )
        users = cursor.fetchall()
    for user in users:
        bot.send_message(user[1], f'Мероприятие <b>{event[1]}</b> добавлено на '
                                  f'<b>{event[4].strftime("%H:%M %d.%m.%Y")}</b> по UTC.')

    five_minutes_time = event[4] + datetime.timedelta(hours=3) - datetime.timedelta(minutes=5)
    if five_minutes_time > datetime.datetime.now():
        schedule.every().day.at(f'{five_minutes_time.strftime("%H:%M")}'). \
            do(scheduled_send_notifications, event_id=event_id, notification_type='five_minutes')
        print(f'Поставлено напоминание на 5 минут | {event_id} {five_minutes_time}')
    ten_minutes_time = event[4] + datetime.timedelta(hours=3) - datetime.timedelta(minutes=10)
    if ten_minutes_time > datetime.datetime.now():
        schedule.every().day.at(f'{ten_minutes_time.strftime("%H:%M")}'). \
            do(scheduled_send_notifications, event_id=event_id, notification_type='ten_minutes')
        print(f'Поставлено напоминание на 10 минут | {event_id} {ten_minutes_time}')
    hour_time = event[4] + datetime.timedelta(hours=3) - datetime.timedelta(hours=1)
    if hour_time > datetime.datetime.now():
        schedule.every().day.at(f'{hour_time.strftime("%H:%M")}'). \
            do(scheduled_send_notifications, event_id=event_id, notification_type='one_hour')
        print(f'Поставлено напоминание на час | {event_id} {hour_time}')


def scheduled_send_notifications(event_id, notification_type):
    """Отправка уведомлений"""
    send_notification(event_id, notification_type)
    return schedule.CancelJob
