#coding:utf-8
'''
Created by github.com/whystar on 2017/12/14.
Used to manually verify the automatic identification.
'''

# import necessary packages
from PyQt5 import QtGui
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import MySQLdb
import sys
import os
import re
from db_cfg import conn
from auto_ident import AutoIdent
auto_ident = AutoIdent(conn)


os.system("pyuic5 manual_verify_ui.ui  -o manual_verify_ui.py")
from manual_verify_ui import Ui_MainWindow

class commentListModel(QStandardItemModel):
	'''
	model class used to show the list of comments
	'''
	def __init__(self, datain,iden_cmt,parent=None, *args):  
		QStandardItemModel.__init__(self, parent, *args)  

		for i in range(0,len(datain)):
			cmt_id,cmt_txt = datain[i]
			item=QStandardItem(cmt_txt)
			font =QFont()
			font.setPointSize(16);
			item.setData(font,Qt.FontRole)
			if i%2 == 0:
				item.setData(QColor(207,207,207,200),Qt.BackgroundRole)
			
			# if a comment contains the reference of a pull-request
			if re.search(r'(#|pull/)\d+',cmt_txt.lower()) != None:
				item.setData(QColor(154,255,154,200),Qt.BackgroundRole)

			# if a comment is a indicative comment
			if len(auto_ident.extract_num_by_rule(cmt_txt)) != 0:
				item.setData(QColor(232,209,57,200),Qt.BackgroundRole)

			# if a comment is the identification comment
			if int(cmt_id) == int(iden_cmt):
				item.setData(QColor(240,128,128,200),Qt.BackgroundRole)

			self.appendRow(item)

		


class mywindow(QMainWindow,Ui_MainWindow):    
	def __init__(self):    
		super(mywindow,self).__init__()  
		# palette1 = QPalette()
		# palette1.setColor(self.backgroundRole(), QColor(166,166,166))   # 设置背景颜色
		# self.setPalette(palette1)

		self.setupUi(self)
		self.bind_slot()

		# reference the current processed project and its candidate duplicate pull-requests
		self.current_prj_id = None
		self.current_dupprs = list() 
		

		# load all the projects from MySQL and store them in a ComboBox
		cursor = conn.cursor()
		cursor.execute("select id, user_name, repo_name from project")
		prjs = cursor.fetchall()
		for prj in prjs:
			self.prj_list.addItem("%8s (%s/%s)"%(prj[0],prj[1],prj[2]))
		prj_id = self.prj_list.currentText().split(" (")[0].strip()
		self.txt_prj_id.setText(prj_id)


		# initial the two lists of comments for dup_pr and mst_pr
		# self.lst_dup_comments.setContextMenuPolicy(Qt.CustomContextMenu) 
		# self.lst_dup_comments.customContextMenuRequested[QPoint].connect(self.lst_comments_ccmr)
		self.lst_dup_comments.clicked.connect(self.itemCk_dup)		
		
		# self.lst_mst_comments.setContextMenuPolicy(Qt.CustomContextMenu) 
		# self.lst_mst_comments.customContextMenuRequested[QPoint].connect(self.lst_comments_ccmr)
		self.lst_mst_comments.clicked.connect(self.itemCk_mst)


		self.ipcmt = None

		self.verify_history = dict()
		if not os.path.exists("verify_history.txt"):
			fp=open("verify_history.txt",'w')
			fp.close()
		with open("verify_history.txt",'r') as tfp:
			for line in tfp.readlines():
				ls = line.split("\t")
				self.verify_history[ls[0].strip()] = int(ls[1].strip())


	# bind slot methods 
	def bind_slot(self):
		self.prj_list.activated.connect(self.prj_sel)
		self.btn_next_pair.clicked.connect(self.load_prj)
		self.btn_yes_dup.clicked.connect(self.yes_dup)
		self.btn_no_dup.clicked.connect(self.no_dup)


	# slot methods to record which comment have been clicked
	def itemCk_mst(self,index):
		self.ipcmt =  self.lst_mst_comments.model().data(index)

	def itemCk_dup(self,index):
		self.ipcmt = self.lst_dup_comments.model().data(index)


	# slot methods to respond to buttons start, yes, and no
	# to start button
	def prj_sel(self):
		prj_id = self.prj_list.currentText().split(" (")[0].strip()
		self.txt_prj_id.setText(prj_id)

	# to yes button
	def yes_dup(self):
		# store the current duplicate prs into table duplicate and record the pointer
		dups = self.txt_dup_pair.text().strip().split("\t")
		cursor = conn.cursor()
		cursor.execute("insert into duplicate(prj_id,dup_pr,mst_pr,idn_cmt) values(%s,%s,%s,%s)",
			(self.current_prj_id,dups[0],dups[1],self.current_iden_cmt))
		conn.commit()

		with open("verify_history.txt",'a') as tfp:
			tfp.write("%s\t%d\n"%(self.current_prj_id, self.verify_history[self.current_prj_id] + 1))
			self.verify_history[self.current_prj_id] += 1

		if len(self.current_dupprs) == 0:
			QMessageBox.information(self, 'Warning', "no more",
										 QMessageBox.Yes, QMessageBox.Yes)
			return 
		self.next_pair()

	# to no button
	def no_dup(self):	
		with open("verify_history.txt",'a') as tfp:
			tfp.write("%s\t%d\n"%(self.current_prj_id, self.verify_history[self.current_prj_id] + 1))
			self.verify_history[self.current_prj_id] += 1

		if len(self.current_dupprs) == 0:
			QMessageBox.information(self, 'Warning', "no more",
										 QMessageBox.Yes, QMessageBox.Yes)
			return 
		self.next_pair()


	# load the candidate duplicate prs for current project
	def load_prj(self):
		prj_id = self.txt_prj_id.text()
		if self.current_prj_id == prj_id:
			print '>> already  load %s'%(prj_id,)
			return 
		print '>> load %s'%(prj_id,)

		dups = list()
		with open("candidate_dups/%s.txt"%(prj_id,),'r') as tfp:
			# record processing history for the loaded project
			if (prj_id not in self.verify_history.keys()):
				self.verify_history[prj_id] = 0

			# begin from last record point  
			for line in tfp.readlines()[self.verify_history[prj_id]:]:
				dup = [item.strip() for item in line.split("\t")]
				dups.append(dup)


		self.current_prj_id = prj_id
		self.current_dupprs = dups
		self.next_pair()

	def next_pair(self):
		if len(self.current_dupprs) == 0:
			QMessageBox.information(self, 'Warning', "no more",
										 QMessageBox.Yes, QMessageBox.Yes)
			return 

		# get next duplicate prs
		dup_prs = self.current_dupprs.pop(0)
		self.lbl_pr_n.setText("%d pr left"%(len(self.current_dupprs)))
		dup_pr, mst_pr, iden_cmt = dup_prs[0],dup_prs[1],dup_prs[2]
		self.current_iden_cmt = iden_cmt
		self.txt_dup_pair.setText("%s\t%s"%(dup_pr,mst_pr))

		# fetch the basic info of prs
		cursor = conn.cursor()
		cursor.execute('select id,author,created_at,title,description from `pull-request` where prj_id=%s and pr_num=%s',
			(self.current_prj_id,dup_pr))
		result = cursor.fetchone()
		self.txt_dup_submitter.setText(result[1])
		self.txt_dup_time.setText(result[2])
		self.txt_dup_title.setText(result[3])
		self.txt_dup_desc.setText(result[4])
		cursor.execute("select id,author,created_at,content from comment where pr_id=%s ",(result[0],))
		result = cursor.fetchall()
		result = sorted(result,cmp=lambda x,y: x[1]<y[1])
		cmts = list()
		for cmt in result:
			cmts.append((cmt[0],"%d\t%s\t%s:\n%s"%(cmt[0],cmt[1],cmt[2],cmt[3])))
			cmts.append((-1,"\n"))
		self.lst_dup_comments.setModel(commentListModel(cmts,iden_cmt,self))		

			
		cursor.execute('select id,author,created_at,title,description from `pull-request` where prj_id=%s and pr_num=%s',
			(self.current_prj_id,mst_pr))
		result = cursor.fetchone()
		self.txt_mst_submitter.setText(result[1])
		self.txt_mst_time.setText(result[2])
		self.txt_mst_title.setText(result[3])
		self.txt_mst_desc.setText(result[4])
		cursor.execute("select id,author,created_at,content from comment where pr_id=%s ",(result[0],))
		result = cursor.fetchall()
		result = sorted(result,cmp=lambda x,y: x[1]<y[1])
		cmts = list()
		for cmt in result:
			cmts.append((cmt[0],"%d\t%s\t%s:\n%s"%(cmt[0],cmt[1],cmt[2],cmt[3])))
			cmts.append((-1,"\n"))
		self.lst_mst_comments.setModel(commentListModel(cmts,iden_cmt,self))




if __name__ == '__main__':

	app = QApplication(sys.argv)
	window = mywindow()

	window.show()
	sys.exit(app.exec_())






	

