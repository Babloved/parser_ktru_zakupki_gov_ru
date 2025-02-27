import sys
import requests
import tqdm
import time
import re
import clipboard
import keyboard
from bs4 import BeautifulSoup
from colorama import init, Fore, Back, Style

# Инициализация colorama
init()

# Заголовки для запросов
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
}

# Базовый URL для запросов
BASE_URL = "https://zakupki.gov.ru"

def check_status_request(response):
    """Проверка статуса ответа от сервера."""
    if response.status_code == 200:
        print(Fore.GREEN + "Сайт ответил положительно!" + Style.RESET_ALL)
    elif response.status_code == 404:
        print(Fore.RED + 'Сайт вернул 404, шаласть не удалась :(' + Style.RESET_ALL)
        raise Exception("404 Not Found")

def get_soup(url):
    """Получение BeautifulSoup объекта по URL."""
    response = requests.get(url, headers=HEADERS)
    check_status_request(response)
    return BeautifulSoup(response.text, 'html.parser')

def process_clipboard_data(clipboard_text):
    """Обработка данных из буфера обмена."""
    clipboard_text = clipboard_text.replace("Больше или равно", '≥').replace("Меньше или равно", '≤').replace("Больше", '>').replace("Меньше", '<').replace(' ', ' ')
    clip_reg_data = re.findall(r'([^\t\r\n]*[^\s]|\n)', clipboard_text)
    clip_reg_data = [j.strip(' ') for j in clip_reg_data]
    dict_data = {}
    idx = 0

    for i in tqdm.tqdm(range(len(clip_reg_data)), bar_format="%s{l_bar}%s{bar}%s{r_bar}" % ("\033[0;32m", "\033[0;32m", "\033[0;32m")):
        if idx and i < idx:
            continue
        if clip_reg_data[i] == '\n':
            idx += 1
            continue
        if clip_reg_data[i] == '\n' or clip_reg_data[i + 1] == '\n':
            dict_data[(clip_reg_data[i], clip_reg_data[i + 1])] = (False, '')
            print(Fore.RED + f'ХАРАКТЕРИСТИКА:"{clip_reg_data[i]}" ИЛИ ЗНАЧЕНИЕ:"{clip_reg_data[i + 1]}" ПУСТОЕ, ЭТО ОШИБКА!' + Style.RESET_ALL)
            print(Fore.RED + f'Возможно непредсказуемое поведение, лучше исправить опечатку, строка: {len(dict_data)}' + Style.RESET_ALL)
            while clip_reg_data[idx] != '\n':
                idx += 1
        else:
            if i + 2 < len(clip_reg_data) and clip_reg_data[i + 2] != '\n':
                dict_data[(clip_reg_data[i], clip_reg_data[i + 1])] = (False, clip_reg_data[i + 2])
                idx += 3
            else:
                dict_data[(clip_reg_data[i], clip_reg_data[i + 1])] = (False, '')
                idx += 2
    return dict_data

def main():
    restart = True
    while restart:
        print(Back.WHITE + Fore.BLACK + "                      ПАРСЕР КТРУ V0.2                     " + Style.RESET_ALL)
        print(Fore.LIGHTWHITE_EX + "Чтобы считать характеристики из буфера обмена нажмите Space" + Style.RESET_ALL)
        keyboard.wait('space')

        try:
            clipboard_text = clipboard.paste()
            dict_data = process_clipboard_data(clipboard_text)

            print("Введите номер КТРУ")
            number_ktru = input()

            print("Приступаем к обработке на сайте")
            search_url = f"{BASE_URL}/epz/ktru/search/results.html?searchString={number_ktru}"
            soup = get_soup(search_url)

            raw_href = soup.find(href=re.compile("itemId")).attrs['href']
            ktru_id = re.findall(r'\d+', raw_href)
            print(f"КТРУ ID:{ktru_id[0]}")

            card_url = f"{BASE_URL}/epz/ktru/ktruCard/commonInfo.html?itemId={ktru_id[0]}"
            soup = get_soup(card_url)

            raw_href = soup.find(href=re.compile("printFormId=")).attrs['href']
            print_form_id = re.findall(r'\d+', raw_href)
            print(f"ID Печатной формы:{print_form_id[0]}")

            print_url = f"{BASE_URL}/epz/ktru/printForm/view.html?printFormId={print_form_id[0]}&source=defaultKtruPF"
            soup = get_soup(print_url)

            raw_table = soup.find('th', string="Наименование характеристики").findParent('table')
            print(Fore.YELLOW + "Таблица КТРУ получена" + Style.RESET_ALL)

            for row in raw_table.find_all('tr'):
                cells = row.find_all('td')
                next_cell_type = False
                next_cell_measur = False

                for cell in cells:
                    if cell.has_attr('rowspan'):
                        if not next_cell_type:
                            cell_name = re.sub(r"(?m)^\s+", "", cell.get_text(strip=True)).replace('\n', ' ')
                            print(f"Характеристика: {cell_name}")
                            next_cell_type = True
                            cur_rowspawn = int(cell['rowspan'])
                        else:
                            next_cell_type = False
                    else:
                        if not next_cell_measur:
                            val = re.sub(r"(?m)^\s+", "", cell.get_text(strip=True)).replace('\n', ' ')
                            val = re.sub(r"≥+(?=\d)", "≥ ", val)
                            val = re.sub(r">+(?=\d)", "> ", val)
                            val = re.sub(r"(?<=\d|[a-z])≤", " ≤", val)
                            val = re.sub(r"(?<=\d|[a-z])<", " <", val)
                            next_cell_measur = True
                        else:
                            measur = re.sub(r"(?m)^\s+", "", cell.get_text(strip=True)).replace('\n', ' ')
                            if (cell_name, val) in dict_data:
                                measur_er = ""
                                print(Fore.LIGHTGREEN_EX + " =>   " + val + " " + measur + Style.RESET_ALL, end='')
                                if measur != dict_data[(cell_name, val)][1]:
                                    measur_er = f" Некорректная ед. изм. ({measur} != {dict_data[(cell_name, val)][1]})"
                                    print(Fore.RED + measur_er + Style.RESET_ALL)
                                else:
                                    print()
                                tp = (cell_name, val)
                                dict_data[(cell_name, val)] = (True, measur_er)
                            else:
                                print(Fore.WHITE + " =|   " + val + " " + measur + Style.RESET_ALL)

                            cur_rowspawn -= 1
                            if cur_rowspawn == 0:
                                print("______________________________________________________________________")

            for key, val in dict_data.items():
                if val[0]:
                    print(Fore.GREEN + f"OK => {key[0]} {key[1]}" + Style.RESET_ALL, end='')
                    if val[1] != '':
                        print(Fore.LIGHTYELLOW_EX + f" <= {val[1]}" + Style.RESET_ALL)
                    else:
                        print()
                else:
                    print(Fore.LIGHTRED_EX + f"ОШИБКА => {key[0]} {key[1]}" + Style.RESET_ALL)

        except requests.exceptions.ConnectionError as e:
            print(Fore.RED, Style.BRIGHT, 'Невозможно установить соединение с сайтом')
        except Exception as e:
            time.sleep(1)
            print(Fore.LIGHTRED_EX + f"Что-то пошло не так, скорее всего ваш буфер некорректен, или ктру не был найден => {e}" + Style.RESET_ALL)

        input_str = ''
        while input_str not in ['y', 'n']:
            print("Для перезапуска нажмите y для выхода n")
            input_str = input().strip()
        restart = input_str == 'y'

if __name__ == "__main__":
    main()
