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
import time

from config import tw_srv1, tw_srv2, now
from models import (
    NewOrderSingle, OrderCancelRequest, ExecutionSingleReport, NewOrderMultileg,
    OrderMassCancelRequest, ExecutionMultilegReport, OrderReplaceRequest
)
from models import create_db

import paramiko
from paramiko.ssh_exception import AuthenticationException
from sqlalchemy.exc import SQLAlchemyError

start_time = time.time()


# скачивает файл логов с указанного сервера по ssh
def download_logfile(settings, srv):
    # paramiko.util.log_to_file('paramiko_lib.log')  # включение логирования ssh подключения

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
    remote_path = '/app/fusion/wire_gate/log/'  # путь к логам на сервере

    # маска для поиска файлов вида support_log.20170927185959998.gz
    pattern = re.compile(r"support_log." + str(log_time) + "\d{7}.gz")

    try:
        files = sftp.listdir(path=remote_path)  # список файлов в папке
        for file in files:
            search = re.search(pattern, file)
            if search:
                log_file = search[0]
                # print(log_file)
                local_path = str(srv) + '_' + log_file  # в виде 1_support_log.20170927185959998.gz

                # скачать файл
                sftp.get(remote_path + log_file, local_path)
                sftp.close()
                ssh.close()

                # распаковать архив
                with gzip.open(local_path, "rb") as f_in, open(local_path[:-3] + '.log', "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

                os.remove(local_path)  # удалить файл архива

        return local_path[:-3] + '.log'

    except IOError as e:
        print('[download_logfile_IOError:]', e)
    except Exception as e:
        print('download_logfile_[Error]', e)


# парсит строку в список из значений полей сообщения
def parse_string(message, srv):
    pattern_timestamp = re.compile(r"(\d+-.*)")
    parse = dict(item.split(' ', 1) for item in message.split(', '))
    result = list(parse.values())

    m = re.search(pattern_timestamp, result[0])
    timestamp = m.group(0)

    sess_id, tw_login = result[1].split('_', 1)
    result[0] = timestamp
    result[1] = sess_id
    result.insert(2, tw_login)
    result.append(srv)

    if result[3] == 'NewOrderSingle':
        sql_obj = NewOrderSingle(
            server_id=result[-1], timestamp=result[0], sess_id=result[1], tw_login=result[2],
            msg_type=result[3], security_id=int(result[11]), price=float(result[10]), order_qty=int(result[13]),
            cl_ord_id=int(result[8]), cl_ord_link_ID=int(result[12]), side=int(result[15]), check_limit=int(result[16]), account=result[17],
            expire_date=result[9], time_in_force=int(result[14])
        )

        return sql_obj


# пишет распарсеную строку в базу данных
def write_to_db(object):
    try:
        session.add(object)
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        print('[write_to_db_SQLAlchemyError]', e)
    except Exception as e:
        session.rollback()
        print('[write_to_db_Error]', e)


# циклично идёт по строкам файла
def file_handling(file_name, srv):
    with open(file_name, 'r') as f:
        for line in f:
            parse_result = parse_string(line, srv)
            if parse_result is not None:
                write_to_db(parse_result)


if __name__ == "__main__":
    try:
        print('Скачиваю файлы')
        file_name1 = download_logfile(tw_srv1, 1)
        print('Файл скачан:', file_name1)
        file_name2 = download_logfile(tw_srv2, 2)
        print('Файл скачан:', file_name2)
        print('Создаю БД')
        session = create_db()
        print(session)
        print('БД создана: ' + now + '.sqlite3')
        print('Открываю файл', file_name1)
        file_handling(file_name1, 1)
        print('Открываю файл', file_name2)
        file_handling(file_name2, 2)
        print('Done!')
        print("--- %s seconds ---" % (time.time() - start_time))

    # except KeyboardInterrupt:
    #     print('Exit')
    except AuthenticationException:
        print('[Main_AuthenticationException] Authentication error! Check login/password')
    except Exception as e:
        print('[Main_Error]', e)


# TODO:
# 1. Сделать логирование
# 2. Работа с файлами логов: открыть нужный файл, циклом идти по строкам и парсить их
# 3. Допилить запись в БД
# 4. Сделать функцию по загрузке указанных вручную логов
