import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p',
    filename='.homework.log'
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    logging.info('Message must be sent!')
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_statuses = requests.get(
        url=ENDPOINT,
        headers=HEADERS,
        params=params
    )
    if homework_statuses.status_code == HTTPStatus.OK:
        return homework_statuses.json()
    raise exceptions.BOT_ERROR('Ошибка status_code != 200')


def check_response(response):
    """Проверяет ответ API на корректность."""
    if type(response) == dict:
        response['current_date']
        homeworks = response['homeworks']
        if type(homeworks) == list:
            return homeworks
        raise exceptions.BOT_ERROR('Ошибка корректности данных list')
    elif response == requests.get(ENDPOINT,
                                  headers=HEADERS,
                                  params=['from_date']):
        if response.status_code == HTTPStatus.OK:
            return
        raise exceptions.BOT_ERROR('Ошибка status_code != 200')
    raise exceptions.BOT_ERROR('Ошибка корректности данных')


def parse_status(homework):
    """Извлекает статус конкретной домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    statuses = HOMEWORK_STATUSES
    if homework_status in statuses:
        verdict = statuses.get(homework_status)
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    raise KeyError('Нет нужных ключей')


def check_tokens():
    """Проверяет доступность переменных."""
    if PRACTICUM_TOKEN is None:
        return False
    elif TELEGRAM_TOKEN is None:
        return False
    elif TELEGRAM_CHAT_ID is None:
        return False
    else:
        return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            new_homework = get_api_answer(current_timestamp)
            homework = check_response(new_homework)[0]
            homework_status = homework['status']
            if homework['status'] != homework_status:
                message = parse_status(homework)
                send_message(bot, message)
                logger.info('Sent message')
            else:
                message = 'Status is not change'
                send_message(bot, message)
                logger.debug('Status is not change')
            current_timestamp = new_homework['current_date']
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
