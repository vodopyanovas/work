#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Данный скрипт скачивает по ssh логи, парсит их и заливает в базу данных.
    Подробнее написано в файле readme.txt (в разработке)
"""

__version__ = '1.5.0'
__author__ = 'Anton Vodopyanov'

import os
import re
import gzip
import shutil
import time
import pyodbc
import logging

from config import tw_srv1, tw_srv2, now
from models import (
    NewOrderSingle, OrderCancelRequest, ExecutionSingleReport, NewOrderMultileg,
    OrderMassCancelRequest, ExecutionMultilegReport, OrderReplaceRequest
)

from models import create_db, drop_old_tables, session

import paramiko
from paramiko.ssh_exception import AuthenticationException
from sqlalchemy.exc import SQLAlchemyError

start_time = time.time()

# конфигурация логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s  %(levelname)-8s  %(module)s  %(message)s')

logfile_handler = logging.FileHandler('parcer_test.log')
logfile_handler.setFormatter(formatter)

logger.addHandler(logfile_handler)


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
                logger.debug(log_file)
                local_path = str(srv) + '_' + log_file  # в виде 1_support_log.20170927185959998.gz

                print('Скачиваю файл:', local_path)
                logger.info('Скачиваю файл: ' + local_path)

                # скачать файл
                sftp.get(remote_path + log_file, local_path)
                sftp.close()
                ssh.close()

                # распаковать архив
                with gzip.open(local_path, "rb") as f_in, open(local_path[:-3] + '.log', "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

                os.remove(local_path)  # удалить файл архива

                # получает размер файла в Байтах, делит на 1024 для получения в КБ и округляет до 2х знаков после запятой
                file_size = round(os.stat(local_path[:-3] + '.log').st_size / 1024, 2)
                print('Файл скачан: ' + local_path[:-3] + '.log' + '  Размер файла: ' + str(file_size) + ' Kb')
                logger.info('Файл скачан: ' + local_path[:-3] + '.log' + '  Размер файла: ' + str(file_size) + ' Kb')

                return local_path[:-3] + '.log'

    except IOError as e:
        print('[download_logfile_IOError:]', e)
        logger.error(e)
    except Exception as e:
        print('[download_logfile_Error]', e)
        logger.exception(e)


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
            timestamp=result[0], sess_id=result[1], tw_login=result[2], msg_type=result[3], cl_ord_id=result[8],
            expire_date=result[9],
            price=result[10],  # float
            security_id=result[11],  # int
            cl_ord_link_ID=result[12],  # int
            order_qty=result[13],  # int
            time_in_force=result[14],  # int
            side=(result[15]),  # int
            check_limit=result[16],  # int
            account=result[17].rstrip(),
            server_id=result[-1]
        )
        return sql_obj

    elif result[3] == 'NewOrderSingleResponse':
        sql_obj = NewOrderSingle(
            timestamp=result[0], sess_id=result[1], tw_login=result[2], msg_type=result[3], cl_ord_id=result[8],
            moment=result[9],
            expire_date=result[10],
            order_id=result[11],  # int
            flags=result[12],
            price=result[13],  # float
            security_id=result[14],  # int
            order_qty=result[15],  # int
            trading_sess_id=result[16],  # int
            cl_ord_link_ID=result[17],  # int
            side=int(result[18]),  # int
            server_id=result[-1]
        )
        return sql_obj

    elif result[3] == 'NewOrderReject':

        sql_obj = NewOrderSingle(
            timestamp=result[0], sess_id=result[1], tw_login=result[2], msg_type=result[3], cl_ord_id=result[8],
            moment=result[9],
            ord_rej_reason=int(result[10]),
            server_id=result[-1]
        )
        return sql_obj

    elif result[3] == 'OrderCancelRequest':

        sql_obj = OrderCancelRequest(
            timestamp=result[0], sess_id=result[1], tw_login=result[2], msg_type=result[3], cl_ord_id=result[8],
            order_id=result[9],  # int
            account=result[10].rstrip(),
            server_id=result[-1]
        )
        return sql_obj

    elif result[3] == 'OrderCancelResponse':

        sql_obj = OrderCancelRequest(
            timestamp=result[0], sess_id=result[1], tw_login=result[2], msg_type=result[3], cl_ord_id=result[8],
            moment=result[9],
            order_id=result[10],  # int
            flags=result[11],
            order_qty=result[12],  # int
            trading_sess_id=result[13],  # int
            cl_ord_link_ID=int(result[14]),
            server_id=result[-1]
        )
        return sql_obj

    elif result[3] == 'OrderCancelReject':

        sql_obj = OrderCancelRequest(
            timestamp=result[0], sess_id=result[1], tw_login=result[2], msg_type=result[3], cl_ord_id=result[8],
            moment=result[9],
            ord_rej_reason=int(result[10]),
            server_id=result[-1]
        )
        return sql_obj

    elif result[3] == 'OrderMassCancelRequest':

        sql_obj = OrderMassCancelRequest(
            timestamp=result[0], sess_id=result[1], tw_login=result[2], msg_type=result[3], cl_ord_id=result[8],
            cl_ord_link_ID=result[9],
            security_id=result[10],
            security_type=result[11],
            side=result[12],
            account=result[13],
            security_group=result[14].rstrip(),
            server_id=result[-1]
        )
        return sql_obj

    elif result[3] == 'OrderMassCancelResponse':

        sql_obj = OrderMassCancelRequest(
            timestamp=result[0], sess_id=result[1], tw_login=result[2], msg_type=result[3], cl_ord_id=result[8],
            moment=result[9],
            total_affected_orders=result[10],
            ord_rej_reason=int(result[11]),
            server_id=result[-1]
        )
        return sql_obj

    elif result[3] == 'OrderReplaceRequest':

        sql_obj = OrderReplaceRequest(
            timestamp=result[0], sess_id=result[1], tw_login=result[2], msg_type=result[3], cl_ord_id=result[8],
            order_id=result[9],
            price=float(result[10]),
            order_qty=result[11],
            cl_ord_link_ID=result[12],
            mode=result[13],
            check_limit=result[14],
            account=result[15].rstrip(),
            server_id=result[-1]
        )
        return sql_obj

    elif result[3] == 'OrderReplaceResponse':

        sql_obj = OrderReplaceRequest(
            timestamp=result[0], sess_id=result[1], tw_login=result[2], msg_type=result[3], cl_ord_id=result[8],
            moment=result[9],
            order_id=result[10],
            prev_order_id=result[11],
            flags=result[12],
            price=float(result[13]),
            order_qty=result[14],
            trading_sess_id=result[15],
            cl_ord_link_ID=int(result[16]),
            server_id=result[-1]
        )
        return sql_obj

    elif result[3] == 'OrderReplaceReject':

        sql_obj = OrderReplaceRequest(
            timestamp=result[0], sess_id=result[1], tw_login=result[2], msg_type=result[3], cl_ord_id=result[8],
            moment=result[9],
            ord_rej_reason=int(result[10]),
            server_id=result[-1]
        )
        return sql_obj

    elif result[3] == 'ExecutionSingleReport':

        sql_obj = ExecutionSingleReport(
            timestamp=result[0], sess_id=result[1], tw_login=result[2], msg_type=result[3], cl_ord_id=result[8],
            moment=result[9],
            order_id=result[10],
            trd_match_ID=result[11],
            flags=result[12],
            last_px=float(result[13]),
            last_qty=result[14],
            order_qty=result[15],
            trading_sess_id=result[16],
            cl_ord_link_ID=result[17],
            security_id=result[18],
            side=int(result[19]),
            server_id=result[-1]
        )
        return sql_obj

    elif result[3] == 'NewOrderMultileg':

        sql_obj = NewOrderMultileg(
            timestamp=result[0], sess_id=result[1], tw_login=result[2], msg_type=result[3], cl_ord_id=result[8],
            expire_date=result[9],
            price=float(result[10]),
            security_id=result[11],
            cl_ord_link_ID=result[12],
            order_qty=result[13],
            time_in_force=result[14],
            side=int(result[15]),
            account=result[16].rstrip(),
            server_id=result[-1]
        )
        return sql_obj

    elif result[3] == 'NewOrderMultilegResponse':

        sql_obj = NewOrderMultileg(
            timestamp=result[0], sess_id=result[1], tw_login=result[2], msg_type=result[3], cl_ord_id=result[8],
            moment=result[9],
            expire_date=result[10],
            order_id=result[11],
            flags=result[12],
            price=float(result[13]),
            security_id=result[14],
            order_qty=result[15],
            trading_sess_id=result[16],
            cl_ord_link_ID=result[17],
            side=int(result[18]),
            server_id=result[-1]
        )
        return sql_obj

    elif result[3] == 'ExecutionMultilegReport':

        sql_obj = ExecutionMultilegReport(
            timestamp=result[0], sess_id=result[1], tw_login=result[2], msg_type=result[3], cl_ord_id=result[8],
            moment=result[9],
            order_id=result[10],
            trd_match_ID=result[11],
            flags=result[12],
            last_px=float(result[13]),
            leg_price=float(result[14]),
            last_qty=result[15],
            order_qty=result[16],
            trading_sess_id=result[17],
            cl_ord_link_ID=result[18],
            security_id=result[19],
            side=int(result[20]),
            server_id=result[-1]
        )
        return sql_obj


# циклично идёт по строкам файла
def file_handling(file_name, srv):
    if file_name:
        print('Читаю файл', file_name)
        logger.info('Читаю файл ' + file_name)

        with open(file_name, 'r') as f:
            for line in f:
                result = parse_string(line, srv)
                if result is not None:
                    session.add(result)  # добавляет распарсеную строку в сессию для записи в базу данных
        print('Заливаю базу')
        logger.info('Заливаю базу')


def main_run():
    file_name1 = download_logfile(tw_srv1, 1)

    if file_name1:
        file_handling(file_name1, 1)
        session.commit()
        print('База залита файлом', file_name1)
        logger.info('База залита файлом ' + file_name1)
        os.remove(file_name1)

    file_name2 = download_logfile(tw_srv2, 2)

    if file_name2:
        file_handling(file_name2, 2)
        session.commit()
        print('База залита файлом', file_name2)
        logger.info('База залита файлом ' + file_name2)
        os.remove(file_name2)

    print('Done!')
    logger.info('Done!')


if __name__ == "__main__":
    logger.info('--- Start ---------------------------------------------------')
    try:
        commands = drop_old_tables()

        for command in commands:
            print(command)
            logger.info(command)

        print('Создаю БД')
        logger.info('Создаю БД')
        create_db()
        print('Таблицы созданы')
        logger.info('Таблицы созданы')

        main_run()

    except KeyboardInterrupt:
        print('Exit')
    except AuthenticationException:
        print('Authentication error! Check login/password')
        logger.critical('Authentication error! Check login/password')
    except SQLAlchemyError as e:
        session.rollback()
        print('[write_to_db_SQLAlchemyError]', e)
        logger.error(e)

    except Exception as e:
        print('[Main_Error]', e)
        logger.exception(e)

    finish_time = time.time() - start_time

    if finish_time > 60:
        finish_time = round(finish_time / 60, 2)
        print(f"[Finished in {finish_time}min]")
        logger.info(f"Finished in {finish_time}min")
    else:
        finish_time = round(finish_time, 2)
        print(f"[Finished in {finish_time}s.]")
        logger.info(f"Finished in {finish_time}s.")
