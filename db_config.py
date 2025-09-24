

import pymysql

def get_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='1536Entartic-8292',
        database='fitigym_db',
        cursorclass=pymysql.cursors.DictCursor
    )
