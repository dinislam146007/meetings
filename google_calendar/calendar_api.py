import datetime
import imaplib
import email
from email.header import decode_header
from google.oauth2 import service_account
import googleapiclient.discovery

# Update your existing GoogleCalendar class
class GoogleCalendar(object):
    """Управление google calendar"""

    def __init__(self):
        credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        self.service = googleapiclient.discovery.build('calendar', 'v3', credentials=credentials)

    def get_events_list(self, calendar_id):
        """Вывод списка всех предстоящих событий"""
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        future_date = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat() + 'Z'  # через неделю
        events_result = self.service.events().list(calendarId=calendar_id,
                                                   timeMin=now,
                                                   timeMax=future_date,
                                                   maxResults=10000, singleEvents=True,
                                                   orderBy='startTime').execute()
        events = events_result.get('items', [])
        parsed_events = []
        for event in events:
            start_time = event['start'].get('dateTime', event['start'].get('date'))
            event_name = event['summary']
            parsed_events.append((start_time, event_name))

        # Fetch and parse emails for events starting with "День рождение"
        birthday_events = self.parse_email_for_birthdays()
        parsed_events.extend(birthday_events)

        return parsed_events

    def parse_email_for_birthdays(self):
        """Parse emails for events starting with 'День рождение'"""
        birthday_events = []
        # Connect to the IMAP server (example assumes Gmail)
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login('mail', 'password')
        mail.select('inbox')

        # Search for emails with subject containing "День рождение"
        status, data = mail.search(None, '(SUBJECT "=?UTF-8?B?0KHQvtCx0YHQsNCy0L7Qu9C10L3QutCw?=")')
        if status == 'OK':
            for num in data[0].split():
                status, msg_data = mail.fetch(num, '(RFC822)')
                if status == 'OK':
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    subject = decode_header(msg["Subject"])[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode()
                    # Add the event to the list if it starts with "День рождение"
                    if subject.startswith("День рождение"):
                        birthday_events.append((None, subject))  # Assuming no start time for email events
        mail.close()
        mail.logout()
        return birthday_events

