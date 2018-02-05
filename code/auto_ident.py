#coding:utf-8
'''
Created by github.com/whystar on 2017/12/14.
Used to automatically identify candidate duplicate pull-requests.
'''

# import necessary packages
import os
import re
from db_cfg import conn
import rules

# this class does the actual identification work 
class AutoIdent():
	def __init__(self,db_conn):
		self.db_conn = db_conn

	def pre_fitler(self,prj_id,src_number,tgt_number):
		'''
		return True if this candidate is filtered, else False
		'''
		cursor.execute('select id,author,created_at,title,description  from `pull-request` where prj_id=%s and pr_num=%s',(prj_id,src_number))
		src_pr = cursor.fetchone()

		# F1: if the matched tgt_number indicates an issue
		cursor.execute('select id,author,created_at,title,description from `pull-request` where prj_id=%s and pr_num=%s',(prj_id,tgt_number))
		tgt_pr = cursor.fetchone()
		if tgt_pr==  None:
			return True

		# F2: if the two prs are submitted by the same author
		tgt_pr_author = tgt_pr[1]
		src_pr_author = src_pr[1]
		if tgt_pr_author == src_pr_author:
			return True
		
		# we call the lately submitted pr as dup_pr and the early submitted pr as mst_pr
		dup_pr_num,mst_pr_num = max(src_number,tgt_number),min(src_number,tgt_number)
		if dup_pr_num == src_number: # the src_number/src_pr indicates the dup_pr
			dup_id, dup_author, dup_time, dup_title, dup_desc = src_pr 
			mst_id = tgt_pr[0]
		else: # the target_number/tgt_pr indicates the dup_pr
			dup_id, dup_author, dup_time, dup_title, dup_desc = tgt_pr
			mst_id = src_pr[0]

		# F3: if the author of the lately submitted pr knows the existence of the early submitted pr
		# F3.1: if the author of dup_pr comment on mst_pr before s/he submit dup_pr
		cursor.execute("select author,created_at,id from comment where pr_id=%s ",(mst_id,))
		cmts = cursor.fetchall()
		flg_know_mst = False
		for cmt in cmts:
			if cmt[0] == dup_author and cmt[1] < dup_time:
				flg_know_mst = True
				break
		if  flg_know_mst:
			return True
		# F3.2 if the author of dup_pr reference mst_pr in the title or description of dup_pr
		if ((dup_title != None and dup_title.find("%d"%mst_pr_num)!=-1) or 
			(dup_desc != None and dup_desc.find("%d"%mst_pr_num)!=-1) ):
			return True

		return False


	def do_job(self,prj_id):

		# used to store all the duplicate prs and the identification comment
		dup_prs = dict()

		# fetch all the pull-requests of the given project
		cursor = self.db_conn.cursor()
		cursor.execute("select id,pr_num,author,created_at from `pull-request` where prj_id=%s",(prj_id,))
		result = cursor.fetchall()
		prs = [item[0] for item in result]

		# store the meta-information of pull-requests
		pr_numbers = {item[0]:int(item[1]) for item in result} 
		pr_authors = {item[0]:item[2] for item in result} 
		pr_times = {item[0]:item[3] for item in result} 

		# iteratively inspect each pull-request
		for pr_id in prs:
			# fetch all the comments of a pullj-request 
			cursor.execute("select id,content,created_at,author from `comment` where pr_id=%s",(pr_id,))
			result = cursor.fetchall() 
			# get the number of candidate duplicate pr contained in each comment
			for comment in result:
				
				comment_text = comment[1]
				

				if comment_text == None:
					continue

				comment_text = comment_text.lower()
				mateched_prns = self.extract_num_by_rule(comment_text)

				# preliminary filter un-real duplicates
				for mateched_prn in mateched_prns:
					src_number = pr_numbers[pr_id]
					tgt_number = int(mateched_prn)

					if self.pre_fitler(prj_id,src_number,tgt_number):
						continue
					
					dup_pr_num,mst_pr_num = max(src_number,tgt_number),min(src_number,tgt_number)
					comment_id, comment_time = comment[0],comment[2] 
					tmp_key = "%d-%d"%(dup_pr_num,mst_pr_num)
					if tmp_key not in dup_prs.keys():
						dup_prs[tmp_key] = (comment_id,comment_time)
					else:
						last_time = dup_prs[tmp_key][1]
						if comment_time < last_time:
							dup_prs[tmp_key] = (comment_id,comment_time)

		# store candidate duplicate prs in files
		print "\t in total: %d"%(len(dup_prs),)
		with open("candidate_dups/%s.txt"%(prj_id,),'w+') as fp:
			fp.truncate()
			for key,value in dup_prs.iteritems():
				dup,mst = key.split("-")
				fp.write("%s\t%s\t%s\n"%(dup,mst,value[0]))
				


	def extract_num_by_rule(self,text):
		'''
		Used to extract the number of candidate duplicate PR contained in the given comment text  
		'''
		prs = list()
		text = text.lower()

		for rule in rules.rules:
			if re.search(rule,text) != None:
				prns = re.findall(rule,text)
				for prn in prns:
					if len(prn) > 0:
						prs.append(prn)

		return prs

if __name__ == '__main__':

	# fetch all the studied project from MySQL
	cursor = conn.cursor()
	cursor.execute("select id from project")
	prjs = [item[0] for item in cursor.fetchall()]

	# create the folder to store candidate duplicate prs for each project
	if not os.path.exists('./candidate_dups'):
		os.makedirs('./candidate_dups')

	# iteratively identify duplicate pull-requests for each project
	for prj in prjs:
		print ">> begin to identify for: %d"%(prj,)
		auto_ident = AutoIdent(conn)
		auto_ident.do_job(prj)
		print "<< done identifying\n"

	

