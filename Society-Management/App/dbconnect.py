import pymysql

HOST     = 'localhost'
USER     = 'root'
PASSWD   = ''
DATABASE = 'society_mysqldb'
def connection():
	conn = pymysql.connect(host = HOST, user = USER, passwd = PASSWD, db = DATABASE)
	cursor = conn.cursor()
	return conn, cursor
