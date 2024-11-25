import sys

import requests
import tqdm
import time
import re

import clipboard
import keyboard

from bs4 import BeautifulSoup

from colorama import init

init()
from colorama import Fore, Back, Style

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}


def CheckStatusRequst(response):
    if response.status_code == 200:
        print(Fore.GREEN + "Сайт ответил положительно!" + Style.RESET_ALL)

    if response.status_code == 404:
        print('Сайт вернул 404, шаласть не удалась :(')
        print(gov_address)
        raise Exception


restart = True
while (restart == True):
    ######### Основной код #########

    print(Back.WHITE + Fore.BLACK + "                      ПАРСЕР КТРУ V0.2                     " + Style.RESET_ALL)

    print(Fore.LIGHTWHITE_EX + "Чтобы считать характеристики из буфера обмена нажмите Space" + Style.RESET_ALL)
    keyboard.wait('space')  # Wait

    try:
        str_clipboard = clipboard.paste()
        str_clipboard = str_clipboard.replace("Больше или равно", '≥').replace("Меньше или равно", '≤').replace("Больше", '>').replace("Меньше", '<').replace(' ', ' ')
        print("Считываю буфер")

        clip_reg_data = re.findall(r'([^\t\r\n]*[^\s]|\n)', str_clipboard)
        clip_reg_data = [j.strip(' ') for j in clip_reg_data]
        dict_data = {}
        print("Обрабатываю данные с буфера")
        read_bar_format = "%s{l_bar}%s{bar}%s{r_bar}" % (
            "\033[0;32m", "\033[0;32m", "\033[0;32m"
        )
        idx = 0
        for i in tqdm.tqdm(range(0, clip_reg_data.__len__()), bar_format=read_bar_format):
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

                if i + 2 < clip_reg_data.__len__() and clip_reg_data[i + 2] != '\n':
                    dict_data[(clip_reg_data[i], clip_reg_data[i + 1])] = (False, clip_reg_data[i + 2])
                    idx += 3
                else:
                    dict_data[(clip_reg_data[i], clip_reg_data[i + 1])] = (False, '')
                    idx += 2

        # Парсим ID КТРУ
        time.sleep(0.5)
        print("Введите номер КТРУ")
        number_ktru = input()

        print("Приступаем к обработке на сайте")
        gov_address = f"https://zakupki.gov.ru/epz/ktru/search/results.html?searchString={number_ktru}"

        r = requests.get(gov_address, headers=headers)
        CheckStatusRequst(r)
        soup = BeautifulSoup(r.text, 'html.parser')
        raw_href = soup.find(href=re.compile("itemId")).attrs['href']
        ktru_id = re.findall(r'\d+', raw_href)
        # считываем текст HTML-документа
        print(f"КТРУ ID:{ktru_id[0]}")

        gov_address = f"https://zakupki.gov.ru/epz/ktru/ktruCard/commonInfo.html?itemId={ktru_id[0]}"
        r = requests.get(gov_address, headers=headers)
        CheckStatusRequst(r)
        soup = BeautifulSoup(r.text, 'html.parser')
        raw_href = soup.find(href=re.compile("printFormId=")).attrs['href']
        print_form_id = re.findall(r'\d+', raw_href)
        print(f"ID Печатной формы:{print_form_id[0]}")

        gov_address = f"https://zakupki.gov.ru/epz/ktru/printForm/view.html?printFormId={print_form_id[0]}&source=defaultKtruPF"
        r = requests.get(gov_address, headers=headers)
        CheckStatusRequst(r)
        soup = BeautifulSoup(r.text, 'html.parser')
        raw_table = soup.find('th', string="Наименование характеристики").findParent('table')
        print(Fore.YELLOW + "Таблица КТРУ получена" + Style.RESET_ALL)
        for row in raw_table.find_all('tr'):
            cells = row.find_all('td')
            next_cell_type = False
            next_cell_measur = False

            for cell in cells:
                if (cell.has_attr('rowspan')):
                    if next_cell_type == False:
                        cell_name = re.sub(r"(?m)^\s+", "", cell.get_text(strip=True)).replace('\n', ' ')
                        print(f"Характеристика: {cell_name}")
                        next_cell_type = True;
                        cur_rowspawn = int(cell['rowspan'])
                    else:
                        next_cell_type = False;
                else:
                    if next_cell_measur == False:
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
            if val[0] == True:
                print(Fore.GREEN + f"OK => {key[0]} {key[1]}" + Style.RESET_ALL, end='')
                if val[1] != '':
                    print(Fore.LIGHTYELLOW_EX + f" <= {val[1]}" + Style.RESET_ALL)
                else:
                    print()
            else:
                print(Fore.LIGHTRED_EX + f"ОШИБКА => {key[0]} {key[1]}" + Style.RESET_ALL)

    except requests.exceptions.ConnectionError as e:
        print(Fore.RED, Style.BRIGHT, 'Невозможно установить соединение с сайтом')
        print(gov_address)

    except Exception as e:
        time.sleep(1)
        print(Fore.LIGHTRED_EX + f"Что-то пошло не так, скорее всего ваш буфер некорректен, или ктру не был найден => {e}" + Style.RESET_ALL)

    input_str = ''
    while input_str != 'y' and input_str != 'n':
        print("Для перезапуска нажмите y для выхода n")
        input_str = input()
        input_str = input_str.replace(' ', '')
    if input_str == 'y':
        restart = True
    else:
        restart = False
