#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Данный скрипт позволяет ...
    Подробнее написано в файле readme.txt
"""

__version__ = '0.4.1'
__author__ = 'Anton Vodopyanov'

import os
import re
import gzip
import shutil

from config import tw_srv1, tw_srv2, now
from models import (
    NewOrderSingle, OrderCancelRequest, ExecutionSingleReport, NewOrderMultileg,
    OrderMassCancelRequest, ExecutionMultilegReport, OrderReplaceRequest
)
from models import create_db

import paramiko
from paramiko.ssh_exception import AuthenticationException


def download_logfile(settings, srv):
    # лог ssh подключения
    # paramiko.util.log_to_file('paramiko_lib.log')

    log_time = int(now) - 1

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect(
        hostname=settings[0],
        username=settings[1],
        password=settings[2],
        port=settings[3]
    )

    sftp = ssh.open_sftp()
    remote_path = '/app/fusion/wire_gate/log/'

    # маска для поиска файлов вида support_log.20170927185959998.gz
    pattern = re.compile(
        r"support_log." + str(log_time) + "\d{7}.gz"
    )

    try:
        files = sftp.listdir(path=remote_path)  # список файлов в папке
        # print(files)
        for file in files:
            # print(file)
            search = re.search(pattern, file)
            if search:
                log_file = search[0]
                # print(log_file)
                local_path = str(srv) + '_' + log_file  # в виде 1_support_log.20170927185959998.gz
                # print(local_path)
                # скачать файл
                sftp.get(remote_path + log_file, local_path)
                sftp.close()
                ssh.close()
                # распаковать архив
                with gzip.open(local_path, "rb") as f_in, open(local_path[:-3] + '.log', "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
                # удалить файл архива
                os.remove(local_path)
        return local_path

    except IOError as e:
        print('IOError:', e)
    except Exception as e:
        print('[Error]', e)


def parser(message):
    pattern_timestamp = re.compile(r"(\d+-.*)")
    parse = dict(item.split(' ', 1) for item in message.split(', '))
    result = list(parse.values())

    m = re.search(pattern_timestamp, result[0])
    timestamp = m.group(0)

    sess_id, tw_login = result[1].split('_', 1)
    result[0] = timestamp
    result[1] = sess_id
    result.insert(2, tw_login)

    return result


if __name__ == "__main__":
    # while True:
    try:
        print('Скачиваю файлы')
        file_name = download_logfile(tw_srv1, 1)
        print('Файл скачан:', file_name)
        file_name = download_logfile(tw_srv2, 2)
        print('Файл скачан:', file_name)
        print('Создаю БД')
        create_db()
        print('БД создана: ' + now + '.sqlite')

    except KeyboardInterrupt:
        print('Exit')
        # break
    except AuthenticationException:
        print('[Error] Authentication error! Check login/password')
    except Exception as e:
        print('[Error]', e)


# TODO:
# с помощью регулярок распарсить строку и записать куда-то
# сделать логирование работы скрипта

# обработать логи, матчить по ClOrdID - дописывать поле OrderID после получения

# подключиться к серверу БД
# записать строку в БД (таблица1/таблица2)
# после записи данных по всему файлу построить view по двум таблицам с сортировкой по времени


# СКРИПТ ДЛЯ БД
# подключиться к серверу
# создать БД, если не создана
# создать таблицы, если не созданы

# pattern = re.compile(
#         r"(\d+-\d+-\d+.\d+:\d+:\d+.\d+.\d+.),.id.(\d*).(tw\w*), \w+ (New\w+|Order\w+[^Q][Request|Response|Reject]).*ClOrdID.(\d+), (.*)")
# timestamp = group(1)
# sess_id = group(2)
# tw_login = group(3)
# name = group(4)
# ClOrdID = group(6)


# (\d+-\d+-\d+.\d+:\d+:\d+.\d+.\d+.),.id.(\d*).(tw\w*), \w+ (New\w+|Order\w+[^Q][Request|Response|Reject]).*ClOrdID.(\d+), (.*)
