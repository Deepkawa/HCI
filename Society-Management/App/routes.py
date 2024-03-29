import json, os, datetime
from functools import wraps
from flask import render_template, request, flash, redirect, url_for, make_response, session, jsonify
from werkzeug.utils import secure_filename
from . import app, allowed_file, read_file
from App  import dbconnect
from App.forms import *
from random import randint

try:
	CONN, CURSOR = dbconnect.connection()
except Exception as e:
	print(e)
	exit()

def user_login_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if 'mainPage' not in session or session['mainPage'] != '/dashboard':
			flash('InLogin to access user pages.')
			return redirect(url_for('index'))
		return f(*args, **kwargs)
	return decorated_function

def admin_login_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if 'mainPage' not in session or session['mainPage'] != '/admin':
			flash('Admin login required to complete the request.')
			return redirect(url_for('index'))
		return f(*args, **kwargs)
	return decorated_function

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
	if('mainPage' in session):
		if(session['mainPage']=='/dashboard'):
			return redirect(url_for('userDashboard'))
		else:
			return redirect(url_for('adminPage'))
	loginForm = LoginForm(request.form)
	if request.method == 'POST':
		if loginForm.validate_on_submit():
			if loginForm.accType.data == 'FlatAcc':
				return redirect(url_for('userDashboard'))
			else:
				return redirect(url_for('adminPage'))
				#to-do: REDIRECT TO ADMIN PAGE
		else:
			for error in loginForm.errors.values():
				flash(str(error[0]))

	return render_template('index.html', form=loginForm)

@app.route('/admin', methods=['GET'])
@admin_login_required
def adminPage():
	addressQuery = "SELECT * FROM society WHERE society_id=%d" % (session['societyId'])
	CURSOR.execute(addressQuery)
	addressRes = CURSOR.fetchone()
	address = [str(addressRes[2]), str(addressRes[3]), str(addressRes[4]), str(addressRes[5])]
	address = ', '.join(address) + '.'

	statsCounter = {'residents': 0, 'flats':0, 'wings': 0, 'admins':0}

	wingsQuery = "SELECT wing_id FROM wing WHERE society_id=%d" % (session['societyId'])
	CURSOR.execute(wingsQuery)
	wings = CURSOR.fetchall()
	statsCounter['wings'] = len(wings)
	flats = []
	if statsCounter['wings'] > 0:
		flatsQuery = "SELECT flat_id FROM flat WHERE wing_id in (%s)" % (','.join([str(x[0]) for x in wings]))
		CURSOR.execute(flatsQuery)
		flats = CURSOR.fetchall()
		statsCounter['flats'] = len(flats)

	if len(flats) > 0:
		residentsQuery = "SELECT COUNT(resident_id) FROM resident WHERE flat_id IN (%s)" % (','.join([str(x[0]) for x in flats]))
		CURSOR.execute(residentsQuery)
		statsCounter['residents'] = CURSOR.fetchone()[0]

	adminCountQuery = "SELECT COUNT(resident_id) FROM admin WHERE society_id=%d" % (session['societyId'])
	CURSOR.execute(adminCountQuery)
	statsCounter['admins'] = CURSOR.fetchone()[0]
	
	newNoticeForm = AddNoticeForm (request.form)
	newBillForm   = AddBillForm   (request.form)

	wingsQuery = "SELECT wing_id, wing_name FROM wing WHERE society_id=%d" % (session['societyId'])
	CURSOR.execute(wingsQuery)

	newBillForm.selectedWings.choices = [(str(x[0]), str(x[1])) for x in CURSOR.fetchall()]

	return render_template('admin/adminpage.html', address=address, counter=statsCounter, noticeForm=newNoticeForm, billForm=newBillForm)

@app.route('/addNotice', methods=['POST'])
@admin_login_required
def addNotice():
	submittedNotice = AddNoticeForm(request.form)
	if not submittedNotice.validate_on_submit():
		for error in submittedNotice.errors.values():
			flash(str(error[0]))
	else:
		notice_id = randint(1,9999)
		addNoticeQuery = "INSERT INTO notices VALUES(%d,%d,'%s',%s','%s')" % (notice_id,session['societyId'],submittedNotice.header.data, submittedNotice.date.data, submittedNotice.body.data)
	return redirect(url_for('adminPage'))

@app.route('/addBill', methods=['POST'])
@admin_login_required
def addBill():
	submittedBill = AddBillForm(request.form)
	print(submittedBill.selectedWings.data)
	#COMPROMISE, VALIDATE DOESNT WORK
	if True or submittedBill.validate_on_submit():
		flash('Added bill')

		for selWing in submittedBill.selectedWings.data:
			getFlatIdQuery = "SELECT flat_id FROM flat WHERE wing_id=%s" % (selWing)
			CURSOR.execute(getFlatIdQuery)
			flats = CURSOR.fetchall()

			for flat_id in flats:
				randomBillId = randint(1,9999)
				addBillQuery = "INSERT INTO basic_maintenance_bill VALUES  \
				(%d, %d, '%s', %d, %d, %d, %d, %d, %d, %d,%d, '%s', NULL) \
				" % (randomBillId, flat_id[0],submittedBill.billDate.data,submittedBill.WATER_CHARGES.data,submittedBill.PROPERTY_TAX.data,submittedBill.ELECTRICITY_CHARGES.data,submittedBill.SINKING_FUNDS.data,submittedBill.PARKING_CHARGES.data,submittedBill.NOC.data,submittedBill.INSURANCE.data,submittedBill.OTHER.data,submittedBill.dueDate.data)
				CURSOR.execute(addBillQuery)
				CURSOR.fetchall()
				CONN.commit()
			print('ADDED BILL')
	else:
		flash('Error bill')

	return redirect(url_for('adminPage'))

@app.route('/logout', methods=['GET'])
def logout():
	session.clear()
	return redirect(url_for('index'))

@app.route('/refreshNotices', methods=['GET', 'POST'])
@user_login_required
def getNoticeList():

	noticeQuery = "SELECT * FROM notices WHERE notices.society_id=%d " % (session['societyId'])
	CURSOR.execute(noticeQuery)

	result = CURSOR.fetchall()
	noticeList = [{'subject':row[2], 'date':str(row[3]), 'body':row[4]} for row in result]
	
	noticeList = json.dumps(noticeList)
	return noticeList


@app.route('/dashboard', methods=['GET'])
@user_login_required
def userDashboard():
	return render_template('user/userdashboard.html')

@app.route('/bills')
@user_login_required
def userBill():
	categories = {'WATER CHARGES':3, 'PROPERTY TAX':4, 'ELECTRICITY CHARGES':5, 'SINKING FUNDS':6, 'PARKING CHARGES':7, 'NOC':8, 'INSURANCE':9, 'OTHER':10}

	billListQuery = "SELECT due_date, amount, bill_num \
					FROM maintenance_bill \
					WHERE flat_id='%d'\
					ORDER BY due_date DESC" % (session['flatId'])

	CURSOR.execute(billListQuery)
	billList = CURSOR.fetchall()
	
	if len(billList) > 0:
		latest_bill = billList[0]
		billList = [{'date': bill[0], 'amount': bill[1]} for bill in billList]

	if len(billList) <= 0:
		currBill = {}
		currBill['date']    = 'N.A.'
		currBill['entries'] = [{'category': x, 'cost': 0} for x in categories]
		currBill['amount']  = 0
		return render_template('user/userbillpage.html', currBill=currBill, billList=billList)


	if len(request.args) <= 0:
		currBillQuery = "SELECT * FROM maintenance_bill WHERE bill_num=%d" % (latest_bill[2])
	else:
		day   = request.args.get('dd')
		month = request.args.get('mm')
		year  = request.args.get('yyyy')
		
		billDate      = '-'.join((year, month, day))
		currBillQuery = "SELECT * FROM maintenance_bill WHERE due_date='%s'" % (billDate)


	CURSOR.execute(currBillQuery)
	currBillResult = CURSOR.fetchone()
	currBill = {}
	currBill['date'] = currBillResult[11]
	currBill['entries'] = [ { 'category' : x, 'cost' : float(currBillResult[categories[x]])} for x in categories]
	currBill['amount'] = currBillResult[12]

	print(currBill['entries'])
	return render_template('user/userbillpage.html', currBill=currBill, billList=billList)

@app.route('/profile')
@user_login_required
def userProfile():
		ownerNameQuery = "SELECT owner_name, pending_dues, profile_img FROM account WHERE acc_name='%s'" % (session['accName'])
		CURSOR.execute(ownerNameQuery)
		ownerRes    = CURSOR.fetchone()
		ownerName   = ownerRes[0]
		pendingDues = ownerRes[1]
		imageUrl    = ownerRes[2]

		if imageUrl is None:
			imageUrl = '#none'
		else:
			imageUrl = 'documents/' + imageUrl

		residentQuery = "SELECT resident_name, contact, resident_id FROM resident WHERE flat_id=%d" % (session['flatId'])
		CURSOR.execute(residentQuery)

		resList = [{'name' :row[0], 'phone': str(row[1]), 'id': str(row[2])} for row in CURSOR.fetchall()]
		residentForm = AddResident(request.form)
		return render_template('user/userprofile.html', imageUrl=imageUrl, ownerName = ownerName, resList = resList, pendingDues = pendingDues, residentForm=residentForm)

@app.route('/editDetails', methods=['POST'])
@user_login_required
def updateUserDetails():
	residentForm  = AddResident(request.form)

	addResQuery = "INSERT INTO resident(flat_id, resident_name, contact) VALUES (%d, '%s', %d)" % (session['flatId'], residentForm.name.data, residentForm.contact.data)
	CURSOR.execute(addResQuery)
	CONN.commit()
	return redirect(url_for('userProfile'))

@app.route('/issues', methods=['GET', 'POST'])
@user_login_required
def getComplaints():
		#get the POST DATA from forms if submitted
	if(request.method == 'POST'):
		related = request.form.get("relatedTo", None)
		if(related == None):
			related = 'None'
		print(related)
		complaint = request.form['complaints']
		print(complaint)
		accId = session['accName']
		now = datetime.datetime.now()
		curr_year = str(now.year)
		if(now.month < 10):
			curr_month = '0' + str(now.month)
		else:
			curr_month = str(now.month)
		if(now.day < 10):
			curr_day = '0' + str(now.day)
		else:
			curr_day = str(now.day)
		curr_date = curr_year + '-' + curr_month + '-' + curr_day
		print(accId)
		print(curr_date)
		CURSOR.execute("INSERT INTO issues(acc_name, issue_date, issue_desc, reported_by, related) VALUES(%s, %s, %s, '', %s)", [accId, curr_date, complaint, related])
		CONN.commit()
		return redirect(url_for('getComplaints'))

	elif(request.method == 'GET'):
		issuesQuery = "SELECT issue_date, issue_desc, related FROM issues WHERE acc_name IN (SELECT acc_name FROM account WHERE flat_id=%d) ORDER BY issue_date" % (session['flatId'])
		CURSOR.execute(issuesQuery)

		issuesList = [{'date': str(row[0]), 'desc': row[1], 'related': row[2]} for row in CURSOR.fetchall()]

		return render_template('user/usercomplaints.html', issuesList = issuesList)


@app.route('/editProfileImage', methods=['POST'])
@user_login_required
def uploadProfileImage():
	if 'file' in request.files:
		profImage = request.files['file']

		if profImage and allowed_file(profImage.filename):
			filename = secure_filename(profImage.filename)
			profImage.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

			imagePathQuery = "UPDATE account SET profile_img='%s' WHERE acc_name='%s'" % (filename, session['accName'])
			CURSOR.execute(imagePathQuery)
			CONN.commit()
		else:
			flash('Invalid file format.')


	else:
		flash('Invalid / Empty file uploaded. Try again')

	return redirect(url_for('userProfile'))

@app.route('/signup', methods=['GET','POST'])
def signupPages():
	societyForm = AddSocietyForm(request.form)
	if 'file' in request.files:
		infoCSV = request.files['file']
		
		if infoCSV and allowed_file(infoCSV.filename):
			filename = secure_filename(infoCSV.filename)
			infoCSV.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
		else:
			flash('Invalid file format.')
			return render_template('signup/societySetupPage.html', societyForm=societyForm)
	if societyForm.validate_on_submit():
		return render_template('signup/societySetupPage.html', societyForm=societyForm)
	for fields,errors in societyForm.errors.items():
		for error in errors:
			flash(getattr(societyForm, fields).label.text + " " + error)
	return render_template('signup/societySetupPage.html', societyForm=societyForm)
	

