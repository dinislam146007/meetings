"""Взаимодействие с базой данных"""
import mysql.connector
import configparser
import os
import contextlib
from google.oauth2 import service_account
from google.oauth2 import service_account
from google_calendar.calendar_api import GoogleCalendar
# ConfigParser
config = configparser.ConfigParser()


@contextlib.contextmanager
def open_connection():
    """Открыть соединение с БД"""
    config.read('config.ini')
    connection = mysql.connector.connect(user=config['Database'].get('login'),
                                         password=config['Database'].get('password'),
                                         host=config['Database'].get('host'),
                                         database=config['Database'].get('database'))
    try:
        yield connection
    finally:
        connection.commit()
        connection.close()
