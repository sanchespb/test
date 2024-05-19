YOUR_BOT_TOKEN = '1072722336:AAFh5YkThk5DCWIgPLp-oIuc_WPX7cpCkEQ'
username = "robot.treasury@ylrus.com"
password = "upznfrmifcxraqfe"
from pprint import pprint

from collections import defaultdict
from telebot import types, TeleBot
from datetime import datetime, timedelta, date
from calendar import day_name
import re
import caldav
from icalendar import vCalAddress, vText, Event, Calendar, vDatetime, vDDDTypes, vDate

events_fetched = None

def get_principal(username, leg_token):
    client = caldav.DAVClient(url="https://caldav.yandex.ru/", username=username, password=leg_token)
    principal = client.principal()
    return principal

my_principal = get_principal(username, password)
calendar = my_principal.calendar(name='Мой календарь')

# Инициализация бота
bot = TeleBot(YOUR_BOT_TOKEN)

# Состояния для взаимодействия с пользователем
class States:
    CHOOSE_WEEK = 0
    DEL_SPOT = 1
    CHOOSE_PARKING_SPOT = 2
    CHOOSE_WEEK_DEL = 4

@bot.message_handler(commands=['start'])
def start(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    button_free_spots = types.KeyboardButton("Свободные места")
    button_delete = types.KeyboardButton("Освободить")
    keyboard.add(button_free_spots, button_delete)
    # Отправка клавиатуры пользователю
    bot.send_message(chat_id=message.chat.id, text="Привет!", reply_markup=keyboard)
    free_slot(message)

# Обработка команды /start
@bot.message_handler( func=lambda message: message.text == 'Свободные места')
def free_slot(message):
    # Устанавливаем начальное состояние
    bot.set_state(message.chat.id, States.CHOOSE_WEEK, message.chat.id)
    
    # Вызываем функцию для выбора недели
    handle_week(message, datetime.now().date())

# Обработка выбора недели
def handle_week(message_or_call, start_date):
    global events_fetched

    # Текущая неделя и дата
    current_week = start_date.isocalendar()[1]
    start_date = start_date - timedelta(start_date.weekday() % 7)
    
    events_fetched = calendar.search(
        start=start_date,
        end=start_date + timedelta(days=5),
        event=True,
        expand=False,
    )

    event_counts = defaultdict(int)
    for event in events_fetched:
        event_date = event.icalendar_component['dtstart'].dt
        event_counts[event_date] += 1

    # Создаем кнопки для выбора недели и даты
    markup = types.InlineKeyboardMarkup()
    btn_prev_week = types.InlineKeyboardButton("◀️ Предыдущая неделя", callback_data=f"week_{current_week-1}")
    btn_next_week = types.InlineKeyboardButton("Следующая неделя ▶️", callback_data=f"week_{current_week+1}")
    markup.row(btn_prev_week, btn_next_week)
    
    for i in range(5):
        day_date = start_date + timedelta(days=i)
        event_count = 6 - event_counts[day_date]
        if not event_count: continue
        btn = types.InlineKeyboardButton(f"{day_name[day_date.weekday()]}, {day_date.strftime('%d.%m')} ({event_count})", callback_data=str(day_date))
        markup.add(btn)
    
    if isinstance(message_or_call, types.Message):
        bot.send_message(chat_id=message_or_call.chat.id, text='🅿️ Выберите дату и неделю:', reply_markup=markup)
    else:
        bot.edit_message_text(chat_id=message_or_call.message.chat.id, message_id=message_or_call.message.message_id,
                              text='🅿️ Выберите дату и неделю:', reply_markup=markup)

# Обработка выбора недели
@bot.callback_query_handler(func=lambda call: bot.get_state(call.message.chat.id, call.message.chat.id) == States.CHOOSE_WEEK)
def handle_week_callback(call):
    # Устанавливаем следующее состояние
    bot.set_state(call.message.chat.id, States.CHOOSE_WEEK, call.message.chat.id)

    print(call.data)
    
    # Обрабатываем выбор недели
    if call.data.startswith("week_"):
        selected_week = int(call.data.split("_")[1])
        # Находим начало недели на основе номера недели
        start_of_week  = date(datetime.now().year, 1, 1) + timedelta(weeks=selected_week-1)
        # Находим первый день недели
        start_of_week  -= timedelta(days=start_of_week.weekday())
        handle_week(call, start_of_week )
    else:
        start_date = datetime.strptime(call.data, '%Y-%m-%d').date()
        handle_date(call, start_date)

# Обработка выбора даты
def handle_date(message_or_call, start_date):
    global events_fetched
    spots = [11, 14, 3, 45, 46, 65]
    emoji = ['🚐', '🚚', '🛻', '🚗', '🚙', '🚕']
    # Устанавливаем следующее состояние
    bot.set_state(message_or_call.message.chat.id, States.CHOOSE_PARKING_SPOT, message_or_call.message.chat.id)
    
    # Создаем кнопки для выбора парковочного места
    markup = types.InlineKeyboardMarkup()

    for current_event  in events_fetched:
        if start_date == current_event.icalendar_component['dtstart'].dt:
            value_to_remove = re.search(r'\d+',current_event.icalendar_component["summary"] )
            if value_to_remove and int(value_to_remove.group(0)) in spots:
                spots.remove(int(value_to_remove.group(0)))
    

    for i, spot in enumerate(spots):
        emoji_index = i % len(emoji)
        btn = types.InlineKeyboardButton(f'{emoji[emoji_index]} Место {spot}', callback_data=f'{start_date}_{spot}')
        markup.add(btn)
    
    if isinstance(message_or_call, types.Message):
        bot.send_message(chat_id=message_or_call.chat.id, text=f'Вы выбрали дату: {start_date.strftime("%d.%m")}', reply_markup=markup)
    else:
        bot.edit_message_text(chat_id=message_or_call.message.chat.id, message_id=message_or_call.message.message_id,
                              text=f'Вы выбрали дату: {start_date.strftime("%d.%m")}', reply_markup=markup)

# Обработка выбора парковочного места
@bot.callback_query_handler(func=lambda call: bot.get_state(call.message.chat.id, call.message.chat.id) == States.CHOOSE_PARKING_SPOT)
def handle_parking(call):
    # Извлекаем дату и номер места
    date_str, spot = call.data.split('_')
    selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    # Сброс состояния
    bot.delete_state(call.message.chat.id, call.message.chat.id)

    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f'Вы выбрали парковочное место {spot} на {selected_date.strftime("%d.%m")}.', reply_markup=None)
    
    attendee = vCalAddress('MAILTO:alexander.demidov@ylrus.com')
    attendee.params['cn'] = vText('alexander.demidov')
    attendee.params['ROLE'] = vText('REQ-PARTICIPANT')
    attendee.params['PARTSTAT'] = vText('ACCEPTED')

    organizer = vCalAddress('MAILTO:robot.treasury@ylrus.com')
    organizer.params['CN'] = vText('robot.treasury')
    organizer.params['ROLE'] = vText('REQ-PARTICIPANT')
    organizer.params['PARTSTAT'] = vText('ACCEPTED')

    new_event = calendar.save_event(
        dtstart=vDate(selected_date),
        dtend=vDate(selected_date + timedelta(days=1)),
        summary=f"Парковочное место {spot}",
        transp='TRANSPARENT',
    )

    new_event.add_attendee(attendee)
    new_event.add_attendee(organizer)
    new_event.add_organizer()

    new_event.save()    

    print( len(calendar.objects()) )

    # Отправка подтверждения пользователю
    bot.send_message(chat_id=call.message.chat.id, text='Парковочное место забронировано успешно!')


@bot.message_handler(func=lambda message: message.text == 'Освободить')
def handle_delete(message, start_date = datetime.now().date()):
    current_week = start_date.isocalendar()[1]
    start_date = start_date - timedelta(start_date.weekday() % 7)
    print(start_date)
    events  = calendar.search(
        start=start_date,
        end=start_date + timedelta(days=5),
        event=True,
        expand=False,
    )

    # Участник, по которому вы хотите отфильтровать события
    example_address = vCalAddress('mailto:alexander.demidov@ylrus.com')
    # Фильтрация событий по участнику
    filtered_events = [event for event in events if example_address in event.icalendar_component.get("ATTENDEE")]
    markup = types.InlineKeyboardMarkup()
    btn_prev_week = types.InlineKeyboardButton("◀️ Предыдущая неделя", callback_data=f"week_{current_week-1}")
    btn_next_week = types.InlineKeyboardButton("Следующая неделя ▶️", callback_data=f"week_{current_week+1}")
    markup.row(btn_prev_week, btn_next_week)

    for event in filtered_events:
        uid = event.icalendar_component["uid"]
        summary = event.icalendar_component["summary"]
        dtstart = event.icalendar_component['dtstart'].dt
        btn = types.InlineKeyboardButton(f'{summary} - {dtstart}', callback_data=f'{uid}')
        markup.add(btn)

    if isinstance(message, types.Message):
        bot.set_state(message.chat.id, States.DEL_SPOT, message.chat.id)
        bot.send_message(chat_id=message.chat.id, text='Выберите место и день для удаления из календаря:', reply_markup=markup)
    else:
        bot.set_state(message.message.chat.id, States.DEL_SPOT, message.message.chat.id)
        bot.edit_message_text(chat_id=message.message.chat.id, message_id=message.message.message_id,
                              text='Выберите место и день для удаления из календаря:', reply_markup=markup)


    # pprint(events[0].icalendar_component)

@bot.callback_query_handler(func=lambda call: bot.get_state(call.message.chat.id, call.message.chat.id) == States.DEL_SPOT)
def handle_week_callback(call):
    # Устанавливаем следующее состояние
    bot.set_state(call.message.chat.id, States.CHOOSE_WEEK_DEL, call.message.chat.id)

    # print(call.data)
    
    # Обрабатываем выбор недели
    if call.data.startswith("week_"):
        selected_week = int(call.data.split("_")[1])
        # Находим начало недели на основе номера недели
        start_of_week  = date(datetime.now().year, 1, 1) + timedelta(weeks=selected_week-1)
        # Находим первый день недели
        start_of_week  -= timedelta(days=start_of_week.weekday())
        print(start_of_week)

        handle_delete(call, start_date = start_of_week )
    else:
        event = calendar.event_by_uid(call.data)
        event.delete()
        bot.delete_state(call.message.chat.id, call.message.chat.id)
        summary = event.icalendar_component["summary"]
        dtstart = event.icalendar_component['dtstart'].dt
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f'Вы освободили {summary} на {dtstart.strftime("%d.%m")}.', reply_markup=None)

# Запуск бота
bot.polling()
