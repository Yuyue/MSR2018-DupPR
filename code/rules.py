#coding:utf-8
'''
Created by github.com/whystar on 2017/12/14.
the complete set of identification rules
'''

rules = [
			# pr number is at end
			r'(?:clos(?:e|ed|ing)|dup(?:licated?)?|super(?:c|s)ee?ded?|obsoleted?|replaced?|redundant|better (?:implementation|solution)'\
				r'|solved|fixed|done|going|merged|addressed|already|land(?:ed|ing)) (?:\w+ ){,5}'\
				r'(?:by|in|with|as|of|in favor of|at|since|via):? (?:\w+:? ){,5}'\
				r'(?:(?:#|https://github.com/(?:[\w\.-]+/)+pull/)(\d+))',  

			# pr number is at the start
			r'(?:#|https://github.com/(?:[\w\.-]+/)+pull/)(\d+):? (?:\w+:? ){,5}'\
				r'(?:better (?:implementation|solution)'\
					r'|dup(?:licate)?'\
					r'|(?:fixe(?:d|s)|obsolete(?:d|s)|replace(?:d|s))'
				r')', 

			# special patters
			r'dup(?:licated?)?:? (?:#|https://github.com/(?:[\w\.-]+/)+pull/)(\d+)' 
		]
