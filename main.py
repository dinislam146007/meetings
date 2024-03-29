"""Основной модуль сервера"""
import threading
from scheduler import schedule_pending, update_events, fill_schedule_after_restart
from bot import bot_polling


if __name__ == '__main__':
    update_events()
    fill_schedule_after_restart()
    threading.Thread(target=schedule_pending).start()
    threading.Thread(target=bot_polling).start()
