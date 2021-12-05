from flask import Flask, render_template, url_for, redirect, session, request, g
import mysql.connector
from functools import wraps
from passlib.hash import sha256_crypt
from wtforms import Form, StringField, PasswordField, IntegerField, validators
#
#-------------------------------------------------------------------------------
#    Start, Connect to DB
#-------------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = '0b579d376dc5dde856e0a0ddca6f403cc8707924ff8d6d31'
def get_mydb():
    mydb = mysql.connector.connect(
        #host="localhost",
        #user="root",
        #passwd="",
        #database="degreeApp"
        host="emccollu.mysql.pythonanywhere-services.com",
        user="emccollu",
        passwd="uedJigTC7YRgKDs",
        database="emccollu$troggy"
    )
    g.mydb = mydb
#-------------------------------------------------------------------------------
#    Pre Login Options
#-------------------------------------------------------------------------------
# Register Form Class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [validators.DataRequired(),validators.EqualTo('confirm', message='Passwords do not match')])
    confirm = PasswordField('Confirm Password')
# User Register
@app.route('/', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))
        get_mydb()
        mydb = g.mydb
        mycursor = mydb.cursor()
        mycursor.execute("INSERT INTO users (name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))
        mydb.commit()
        mycursor.close()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)
# Login, main page
@app.route('/login', methods=['GET', 'POST'])
def login():
    get_mydb()
    mydb = g.mydb
    if request.method == 'POST':
        username = request.form['username']
        password_candidate = request.form['password']
        mycursor = mydb.cursor(dictionary=True)
        mycursor.execute("SELECT * FROM users WHERE username = %s", [username])
        result = mycursor.fetchone()
        if result:
            password = result['password']
            if sha256_crypt.verify(password_candidate, password):
                session['logged_in'] = True
                session['username'] = username
                session['name'] = result['name']
                return redirect(url_for('dashboard', username=username))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            mycursor.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)
    return render_template('login.html')
# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('login'))
    return wrap
#-------------------------------------------------------------------------------
#    Logout
#-------------------------------------------------------------------------------
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    return redirect(url_for('login'))

#-------------------------------------------------------------------------------
#    Global Variable Assignments
#-------------------------------------------------------------------------------
def get_studinfo():
    mydb = g.mydb
    mycursor = mydb.cursor()
    mycursor.execute("UPDATE SampleStudent A INNER JOIN AllCourses B ON A.CourseNum = B.CourseNum SET A.CourseName = B.CourseName WHERE A.UserName = %s", [session['username']])
    mydb.commit()
    mycursor.execute("SELECT A.CourseNum, A.Credits, A.idSampleStudent, A.Grade, A.CourseName FROM SampleStudent A WHERE A.UserName = %s", [session['username']])
    courses = mycursor.fetchall()
    mycursor.close()
    session['courses'] = courses
    credits = 0
    courseamount=0
    for item in courses:
        credits+=item[1]
        courseamount+=1
    session['credits'] = float(credits)
    session['courseamt'] = courseamount


def get_grades():
    if session['courseamt'] != 0:
        def sortLost(val):
            return val[5]
        mydb = g.mydb
        mycursor = mydb.cursor()
        mycursor.execute("SELECT B.*, A.CourseNum FROM SampleStudent A JOIN gradePoints B ON A.Grade = B.Grade AND A.Credits = B.Credits AND A.UserName = %s", [session['username']])
        results = mycursor.fetchall()
        mycursor.close()
        list = []
        studPnts = 0.0
        totalPnts = 0.0
        for row in results:
            if row[1]!="A":
                place = [str(row[6]), str(row[1]), str(row[2]), float(row[3]), float(row[4]), float(row[5])]
                list.append(place)
            totalPnts += float(row[3])
            studPnts += float(row[4])
        list.sort(key = sortLost, reverse=True)
        session['grades'] = list
        session['possPnts'] = totalPnts
        session['studPnts'] = studPnts
        credits = float(session['credits'])
        studGPA = studPnts/credits
        studGPA = format(studGPA, '.2f')
        session['studGPA'] = studGPA
        studGrade = "F"
        tmpx = 0
        studGPA = float(studGPA)
        if (studGPA >= 1.00) and (studGPA < 1.67):
            studGrade = "D"
            tmpx = 1.00
        elif (studGPA >= 1.67) and (studGPA < 2.00):
            studGrade = "C-"
            tmpx = 1.67
        elif (studGPA >= 2.00) and (studGPA < 2.33):
            studGrade = "C"
            tmpx = 2.00
        elif (studGPA < 2.67) and (studGPA >= 2.33):
            studGrade = "C+"
            tmpx = 2.33
        elif (studGPA < 3.00) and (studGPA >= 2.67):
            studGrade = "B-"
            tmpx = 2.67
        elif (studGPA < 3.33) and (studGPA >= 3.00):
            studGrade = "B"
            tmpx = 3.00
        elif (studGPA < 3.67) and (studGPA >= 3.33):
            studGrade = "B+"
            tmpx = 3.33
        elif (studGPA < 4.00) and (studGPA >= 3.67):
            studGrade = "A-"
            tmpx = 3.67
        elif (studGPA == 4.00):
            studGrade = "A"
        session['studGrade'] = studGrade
        tmp = ((tmpx + 0.33)*credits)-studPnts
        if tmp >= 0:
            session['nextGrade'] = tmp
        else:
            session['nextGrade'] = 0
    else:
        session['grades'] = 0
#-------------------------------------------------------------------------------
#    General Reqs
# FirstSeminar,SecondSeminar,English,Constitution,Mathematics,Humanities,Fine Art,Life Phys,Ayl Think,Social,International,Multicultural
#-------------------------------------------------------------------------------
def get_genreqs():
    mydb = g.mydb
    cursor = mydb.cursor()
    gentest = []
    dashgen = []
    # ========FirstSeminar==========================================
    credits = 0
    cursor.execute("SELECT A.CourseNum, A.Credits FROM SampleStudent A JOIN FirstSeminar B ON A.CourseNum = B.CourseNum AND A.UserName= %s;", [session['username']])
    results = cursor.fetchall()
    for row in results:
        credits = row[1]
    if credits>=2:
        tmp = [2, "success"]
        dashgen.append(tmp)
    else:
        tmp = (credits,"nosuccess")
        dashgen.append(tmp)
    gentest.append(results)
    # ========SecondSeminar==========================================
    credits = 0
    cursor.execute("SELECT A.CourseNum, A.Credits FROM SampleStudent A JOIN SecondSeminar B ON A.CourseNum = B.CourseNum AND A.UserName= %s;", [session['username']])
    results = cursor.fetchall()
    for row in results:
        credits = row[1]
    if credits>=3:
        tmp = [3, "success"]
        dashgen.append(tmp)
    else:
        tmp = (credits,"nosuccess")
        dashgen.append(tmp)
    gentest.append(results)
    # ========English==========================================
    credits = 0
    cursor.execute("SELECT A.CourseNum, A.Credits FROM SampleStudent A JOIN English B ON A.CourseNum = B.CourseNum AND A.UserName= %s;", [session['username']])
    results = cursor.fetchall()
    for row in results:
        credits = credits + row[1]
    if credits>=6:
        tmp = [6, "success"]
        dashgen.append(tmp)
    else:
        tmp = (credits,"nosuccess")
        dashgen.append(tmp)
    gentest.append(results)
    # ========Constitution=====================================
    credits = 0
    cursor.execute("SELECT A.CourseNum, A.Credits FROM SampleStudent A JOIN Constitution B ON A.CourseNum = B.CourseNum AND A.UserName= %s;", [session['username']])
    results = cursor.fetchall()
    for row in results:
        credits = credits + row[1]
    if credits>=4:
        tmp = [4, "success"]
        dashgen.append(tmp)
    else:
        tmp = (credits,"nosuccess")
        dashgen.append(tmp)
    gentest.append(results)
    # ========Mathematics======================================
    credits = 0
    cursor.execute("SELECT A.CourseNum, A.Credits FROM SampleStudent A JOIN Mathematics B ON A.CourseNum = B.CourseNum AND A.UserName= %s;", [session['username']])
    results = cursor.fetchall()
    for row in results:
        credits = credits + row[1]
    if credits>=3:
        tmp = [3, "success"]
        dashgen.append(tmp)
    else:
        tmp = (credits,"nosuccess")
        dashgen.append(tmp)
    gentest.append(results)
    # ========Humanities====================================
    credits = 0
    cursor.execute("SELECT A.CourseNum, A.Credits FROM SampleStudent A JOIN Humanities B ON A.CourseNum = B.CourseNum AND A.UserName= %s;", [session['username']])
    results = cursor.fetchall()
    for row in results:
        credits = credits + row[1]
    if credits>=6:
        tmp = [6, "success"]
        dashgen.append(tmp)
    else:
        tmp = (credits,"nosuccess")
        dashgen.append(tmp)
    gentest.append(results)
    # ========Fine Art====================================
    credits = 0
    cursor.execute("SELECT A.CourseNum, A.Credits FROM SampleStudent A JOIN FineArts B ON A.CourseNum = B.CourseNum AND A.UserName= %s;", [session['username']])
    results = cursor.fetchall()
    for row in results:
        credits = credits + row[1]
    if credits>=3:
        tmp = [3, "success"]
        dashgen.append(tmp)
    else:
        tmp = (credits,"nosuccess")
        dashgen.append(tmp)
    gentest.append(results)
    # ========Life Phys====================================
    credits = 0
    cursor.execute("SELECT A.CourseNum, A.Credits FROM SampleStudent A JOIN LifePhysical B ON A.CourseNum = B.CourseNum AND A.UserName= %s;", [session['username']])
    results = cursor.fetchall()
    for row in results:
        credits = credits + row[1]
    if credits>=6:
        tmp = [6, "success"]
        dashgen.append(tmp)
    else:
        tmp = (credits,"nosuccess")
        dashgen.append(tmp)
    gentest.append(results)
    # ========Ayl Think====================================
    credits = 0
    cursor.execute("SELECT A.CourseNum, A.Credits FROM SampleStudent A JOIN AnyltThink B ON A.CourseNum = B.CourseNum AND A.UserName= %s;", [session['username']])
    results = cursor.fetchall()
    for row in results:
        credits = credits + row[1]
    if credits>=3:
        tmp = [3, "success"]
        dashgen.append(tmp)
    else:
        tmp = (credits,"nosuccess")
        dashgen.append(tmp)
    gentest.append(results)
    # ========Social====================================
    credits = 0
    cursor.execute("SELECT A.CourseNum, A.Credits FROM SampleStudent A JOIN SocialScience B ON A.CourseNum = B.CourseNum AND A.UserName= %s;", [session['username']])
    results = cursor.fetchall()
    for row in results:
        credits = credits + row[1]
    if credits>=9:
        tmp = [9, "success"]
        dashgen.append(tmp)
    else:
        tmp = (credits,"nosuccess")
        dashgen.append(tmp)
    gentest.append(results)
    # ========International==================================
    credits = 0
    cursor.execute("SELECT A.CourseNum, A.Credits FROM SampleStudent A JOIN International B ON A.CourseNum = B.CourseNum AND A.UserName= %s;", [session['username']])
    results = cursor.fetchall()
    for row in results:
        credits = credits + row[1]
    if credits>=3:
        tmp = [3, "success"]
        dashgen.append(tmp)
    else:
        tmp = (credits,"nosuccess")
        dashgen.append(tmp)
    gentest.append(results)
    # ========Multicultural====================================
    credits = 0
    cursor.execute("SELECT A.CourseNum, A.Credits FROM SampleStudent A JOIN Multicultural B ON A.CourseNum = B.CourseNum AND A.UserName= %s;", [session['username']])
    results = cursor.fetchall()
    for row in results:
        credits = credits + row[1]
    if credits>=3:
        tmp = [3, "success"]
        dashgen.append(tmp)
    else:
        tmp = (credits,"nosuccess")
        dashgen.append(tmp)
    gentest.append(results)
    cursor.close()
    session['gentest'] = gentest
    session['dashgen'] = dashgen
    earned = 0
    for item in dashgen:
        earned+=item[0]
    if earned >= 51:
        earned = 51
    needed = 51 - earned
    session['needgen'] = needed
    session['requiregen'] = ["1st Year Seminar","2nd Year Seminar","English Composition","Constitutions","Mathematics","Humanities","Fine Arts","Life/Phys Sciences","Analytical Thinking","Social Sciences","Multicultural","International"]
#-------------------------------------------------------------------------------
#      Render Pages
#-------------------------------------------------------------------------------
#@app.route('/dashboard')
@app.route('/dashboard')
@is_logged_in
def dashboard():
    get_mydb()
    get_studinfo()
    return render_template('dashboard.html')
@app.route('/general')
@is_logged_in
def general():
    get_mydb()
    get_genreqs()
    return render_template('general.html')
@app.route('/grades')
@is_logged_in
def grades():
    get_mydb()
    get_grades()
    if session['courseamt']!=0:
        gradeDict = {'acount': 0, 'amcount': 0, 'bpcount': 0, 'bcount': 0, 'bmcount': 0, 'cpcount': 0, 'ccount': 0, 'cmcount': 0, 'dpcount': 0, 'dcount': 0, 'fcount': 0}
        for item in session['grades']:
            if item[1]=='A-':
                gradeDict['amcount']+=1
            elif item[1]=='A':
                gradeDict['acount']+=1
            elif item[1]=='B-':
                gradeDict['bmcount']+=1
            elif item[1]=='B+':
                gradeDict['bpcount']+=1
            elif item[1]=='B':
                gradeDict['bcount']+=1
            elif item[1]=='C-':
                gradeDict['cmcount']+=1
            elif item[1]=='C+':
                gradeDict['cpcount']+=1
            elif item[1]=='C':
                gradeDict['ccount']+=1
            elif item[1]=='D+':
                gradeDict['dpcount']+=1
            elif item[1]=='D':
                gradeDict['dcount']+=1
            elif item[1]=='F':
                gradeDict['fcount']+=1
        return render_template('grades.html', gradeDict=gradeDict)
    return render_template('grades.html')
@app.route('/information')
def information():
    return render_template('information.html')
#-------------------------------------------------------------------------------
#    Add/Delete Courses
#-------------------------------------------------------------------------------
class AddCourseForm(Form):
    coursenum = StringField('Course Number', [validators.required(), validators.Length(min=5, max=9)])
    grade = StringField('Grade', [validators.optional(), validators.Length(max=3)])
    credits = IntegerField('Credits', [validators.required()])
# Add Article
@app.route('/courselist', methods=['GET'])
@is_logged_in
def courselist():
    get_mydb()
    get_studinfo()
    form = AddCourseForm(request.form)
    return render_template('addCourse.html', form=form)
@app.route('/courselist', methods=['POST'])
@is_logged_in
def addCourse():
    get_mydb()
    get_studinfo()
    form = AddCourseForm(request.form)
    CourseNum = form.coursenum.data
    Grade = form.grade.data
    Credits = form.credits.data
    mydb = g.mydb
    mycursor = mydb.cursor()
    mycursor.execute("INSERT INTO SampleStudent (CourseNum, Grade, Credits, UserName) VALUES (%s, %s, %s, %s)",(CourseNum, Grade, Credits, session['username']))
    mydb.commit()
    mycursor.close()
    return redirect(url_for('courselist', form=form))
    #return render_template('addCourse.html', form=form)
# Delete Courses
@app.route('/delCourse/<int:id>', methods=['POST'])
@is_logged_in
def delCourse(id):
    get_mydb()
    mydb = g.mydb
    mycursor = mydb.cursor()
    mycursor.execute("DELETE FROM SampleStudent WHERE idSampleStudent = %s", [id])
    mydb.commit()
    mycursor.close()
    get_studinfo()
    return redirect(url_for('courselist'))

if __name__ == "__main__":
    app.secret_key = '0b579d376dc5dde856e0a0ddca6f403cc8707924ff8d6d31'
    app.run(debug=True)
