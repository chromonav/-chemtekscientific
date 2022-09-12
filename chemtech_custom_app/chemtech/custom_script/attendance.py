import frappe
import time 
import json
from dateutil import parser
from datetime import datetime, date

def get_shift_time_detail(doc):
	#print("~~~~~~~~~~~~~~~~doc",doc)
	doc = json.loads(doc)
	#print("dddddddddoc = ",doc)
	early_by_time=0
	late_by_time=0
	shift = doc.get('shift')
	#start_time = doc.get('start_time')
	shift_start_time = frappe.db.get_value("Shift Type",{'name':shift},"start_time")
	shift_start_time2 = datetime.strptime(str(shift_start_time),'%H:%M:%S').time()
	frm_start_time = datetime.strptime(doc.get('start_time'), '%H:%M:%S').time()
	
	if frm_start_time < shift_start_time2:
		#print("*****************",shift_start_time2,frm_start_time)
		early_by_time = datetime.combine(date.today(), shift_start_time2) - datetime.combine(date.today(), frm_start_time)
		#print("++++++++++++early_by_time",early_by_time)
		return early_by_time,late_by_time

	if frm_start_time > shift_start_time2:
		#print("*****************",shift_start_time2,frm_start_time)
		late_by_time = datetime.combine(date.today(), frm_start_time) - datetime.combine(date.today(), shift_start_time2)
		#print("++++++++++++early_by_time",early_by_time)

		return early_by_time,late_by_time


