#coding:utf-8
'''
Created by github.com/whystar on 2017/12/14.
Used to configure the database
'''
import MySQLdb
# configure the db connection to MySQL
host,user,passwd,db = "localhost", "starlee", "1234","duppr"
conn = MySQLdb.connect(host,user,passwd,db,charset='utf8')

