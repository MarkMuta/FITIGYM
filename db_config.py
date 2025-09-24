

import pymysql

def get_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='your-database-password',
        database='fitigym_db',
        cursorclass=pymysql.cursors.DictCursor
    )
