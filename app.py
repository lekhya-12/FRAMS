from flask import Flask,render_template,request,flash,jsonify,redirect,url_for,session,send_file
import pickle
import pandas as pd
import cv2
import numpy as np
import face_recognition
import os
import pickle
from datetime import datetime
from datetime import date
import sqlite3

name="amlan"
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Global set to track students marked in the current session
marked_students = set()

# Database setup
conn = sqlite3.connect('information.db')
conn.execute('''CREATE TABLE IF NOT EXISTS Admin (username TEXT PRIMARY KEY, password TEXT NOT NULL)''')
conn.commit()
conn.close()

# Database setup
conn = sqlite3.connect('information.db')
conn.execute('''CREATE TABLE IF NOT EXISTS Teachers (id VARCHAR PRIMARY KEY, name TEXT, dept TEXT, email TEXT, phone_number TEXT, password TEXT)''')
conn.execute('''CREATE TABLE IF NOT EXISTS Students (roll_no VARCHAR PRIMARY KEY, name TEXT, year TEXT, email TEXT, phone_number TEXT, password TEXT, branch TEXT)''')
conn.execute('''CREATE TABLE IF NOT EXISTS Subjects (
    code VARCHAR PRIMARY KEY ,
    name TEXT UNIQUE NOT NULL,
    year INTEGER NOT NULL,
    semester INTEGER NOT NULL,
    description TEXT
)''')
conn.commit()
conn.close()

# Insert an admin user (Run Once)
conn = sqlite3.connect('information.db')
conn.execute("INSERT OR IGNORE INTO Admin (username, password) VALUES ('admin', 'admin123')")
conn.commit()
conn.close()

def update_encodings():
    images = []
    classNames = []
    myList = os.listdir('Training images')
    print("Images found:", myList)

    for cl in myList:
        curImg = cv2.imread(f'Training images/{cl}')
        images.append(curImg)
        classNames.append(os.path.splitext(cl)[0])

    def findEncodings(images):
        encodeList = []
        for img in images:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            encode = face_recognition.face_encodings(img)
            if encode:
                encodeList.append(encode[0])
            else:
                print(f"Skipping {img} - can't be encoded")
        return encodeList

    print("Encoding images...")
    encodeListKnown = findEncodings(images)

    # Save encodings
    with open('encodings.pickle', 'wb') as f:
        pickle.dump((encodeListKnown, classNames), f)

    print("Encodings saved successfully!")


@app.route('/download_attendance')
def download_attendance():
    date = request.args.get('date')
    month = request.args.get('month')
    subject = request.args.get('subject')

    conn = sqlite3.connect('information.db')
    cursor = conn.cursor()

    query = "SELECT rollno, name, time, date, subject FROM Attendance WHERE 1=1"
    params = []

    if date:
        query += " AND date = ?"
        params.append(date)
    if month:
        query += " AND strftime('%m', date) = ?"
        params.append(month.zfill(2))  # Ensure month is 2 digits
    if subject:
        query += " AND subject = ?"
        params.append(subject)

    cursor.execute(query, params)
    data = cursor.fetchall()
    conn.close()

    # Convert to DataFrame
    df = pd.DataFrame(data, columns=["Roll Number", "Student Name", "Time", "Date", "Subject"])

    # Save to an Excel file
    filename = "attendance_report.xlsx"
    df.to_excel(filename, index=False)

    # Send file as response
    return send_file(filename, as_attachment=True)

@app.route('/view_attendance', methods=['GET'])
def view_attendance():
    conn = sqlite3.connect('information.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Fetch subjects dynamically from the Subjects table
    cur.execute("SELECT DISTINCT name FROM Subjects")
    subjects = [row["name"] for row in cur.fetchall()]
    
    conn.close()
    
    return render_template('ViewAttendance.html', subjects=subjects)

# Route to filter attendance based on criteria
@app.route('/filter_attendance', methods=['POST'])
def filter_attendance():
    data = request.get_json()
    selected_date = data.get('date')
    # weeks = data.get('weeks')
    month = data.get('month')
    subject = data.get('subject')

    conn = sqlite3.connect('information.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = "SELECT * FROM Attendance WHERE 1=1"
    params = []

    # Filter by date
    if selected_date:
        query += " AND Date = ?"
        params.append(selected_date)

    # Filter by weeks
    # if weeks:
    #     weeks_ago = datetime.now() - timedelta(weeks=int(weeks))
    #     query += " AND Date >= ?"
    #     params.append(weeks_ago.strftime("%Y-%m-%d"))

    # Filter by month
    if month:
        query += " AND strftime('%m', Date) = ?"
        params.append(month.zfill(2))  # Ensure two-digit format

    # Filter by subject
    if subject:
        query += " AND Subject = ?"
        params.append(subject)

    cur.execute(query, params)
    attendance_records = cur.fetchall()
    conn.close()

    # Convert results to JSON
    attendance_list = [
        {
            "rollno": row["ROLLNO"],
            "name": row["NAME"],
            # "roll_no": row["Roll_Number"],
            # "subject": row["Subject"],
            # "date": row["Date"],
            # "status": row["Status"]
            "time": row["Time"],
            "date": row["Date"],
            "subject": row["Subject"]
        } 
        for row in attendance_records
    ]

    return jsonify(attendance_list)

@app.route('/add_subject', methods=['POST'])
def add_subject():
    name = request.form['name']
    code = request.form['code']
    year = request.form['year']
    semester = request.form['semester']
    description = request.form['description']

    conn = sqlite3.connect('information.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Subjects (name, code, year, semester, description) VALUES (?, ?, ?, ?, ?)",
                   (name.upper(), code, year, semester, description.upper()))
    conn.commit()
    conn.close()
    # return "Subject Added Successfully!"
    # return render_template('ManageSubjects.html')
    return redirect(url_for('manage_subjects'))

@app.route('/get_subjects')
def get_subjects():
    conn = sqlite3.connect('information.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Subjects")
    subjects = cursor.fetchall()
    conn.commit()
    conn.close()

    # return jsonify([{'id': row[0], 'name': row[1], 'code': row[2], 'year': row[3], 'semester': row[4], 'description': row[5]} for row in subjects])
    return render_template('ManageSubjects.html', rows=subjects)


@app.route('/teacher_login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == "POST":
        tid = request.form.get('tid')
        password = request.form.get('password')

        conn = sqlite3.connect('information.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM Teachers WHERE id=? AND password=?", (tid, password))
        teacher = cur.fetchone()
        conn.commit()
        conn.close()

        if teacher:
            session['teacher_name'] = teacher[1]
            session['dept'] = teacher[2]
            session['email'] = teacher[3]
            session['phn'] = teacher[4]
            return redirect(url_for('teacher_dashboard'))
        else:
            return render_template('TeacherLogin.html',message="Invalid Teacher ID or Password")

    return render_template('TeacherLogin.html',message="Please enter Teacher ID and Password")


@app.route('/teacher_register', methods=['GET', 'POST'])
def teacher_register():
    if request.method == "POST":
        name = request.form.get('name')
        tid=request.form.get('tid')
        dept = request.form.get('dept')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        password = request.form.get('password')

        conn = sqlite3.connect('information.db')
        # try:
        conn.execute("INSERT INTO Teachers (id,name, dept, email, phone_number, password) VALUES (?,?, ?, ?, ?, ?)",
                         (tid,name.upper(), dept.upper(), email, phone_number, password))
        conn.commit()
        conn.close()

        return render_template('TeacherLogin.html')

    return render_template('TeacherRegister.html')

@app.route('/student_register', methods=['GET', 'POST'])
def student_register():
    if request.method == "POST":
        name = request.form.get('name')
        rollno=request.form.get('rollno')
        branch=request.form.get('branch')
        year = request.form.get('year')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        password = request.form.get('password')

        conn = sqlite3.connect('information.db')
        conn.execute("INSERT INTO Students (roll_no, name, year, email, phone_number, password, branch) VALUES (?,?, ?, ?, ?, ?, ?)",
                         (rollno,name.upper(), year, email, phone_number, password, branch.upper()))
        conn.commit()
        conn.close()
        update_encodings()
        return render_template('StudentLogin.html')

    return render_template('StudentRegister.html')

@app.route("/teacher_dashboard")
def teacher_dashboard():
    teacher_name = session.get("teacher_name")
    teacher_dept = session.get("dept")
    teacher_email = session.get("email")
    teacher_phn = session.get("phn")
    if not teacher_name and not teacher_dept and not teacher_email and not teacher_phn:
        return "Unauthorized access. Please log in."
    
    conn = sqlite3.connect('information.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch total subjects
    cursor.execute("SELECT COUNT(*) FROM Subjects")
    total_subjects = cursor.fetchone()[0]

    # Fetch total students
    cursor.execute("SELECT COUNT(*) FROM Students")
    total_students = cursor.fetchone()[0]

    conn.close()

    return render_template('TeacherDashboard.html', teacher_name=teacher_name, teacher_dept=teacher_dept, teacher_email=teacher_email, teacher_phn = teacher_phn,
                           total_subjects=total_subjects, total_students=total_students)

@app.route("/student_dashboard")
def student_dashboard():
    stu_name = session.get("student_name")  # Fetch logged-in student's name
    stu_roll = session.get("stu_roll")
    stu_branch = session.get("stu_branch")
    stu_email = session.get("stu_email")
    stu_phn = session.get("stu_phn")
    if not stu_name and not stu_roll and not stu_email and not stu_branch and not stu_phn :
        return "Unauthorized access. Please log in."

    conn = sqlite3.connect("information.db")
    cursor = conn.cursor()

    # Fetch all subjects (including those the student hasn't attended)
    cursor.execute("SELECT DISTINCT Subject FROM Attendance")
    all_subjects = [row[0] for row in cursor.fetchall()]  # List of all subjects

    # Fetch subject-wise attendance for the student
    cursor.execute("SELECT Subject, COUNT(*) FROM Attendance WHERE NAME = ? GROUP BY Subject", (stu_name.upper(),))
    attendance_data = dict(cursor.fetchall())  # Convert to dictionary {subject: attended_count}

    # Fetch total classes held for each subject
    cursor.execute("SELECT Subject, COUNT(*) FROM Attendance GROUP BY Subject")
    total_classes_dict = dict(cursor.fetchall())  # Convert to dictionary {subject: total_classes}

    conn.close()

    # Create a complete subject-wise attendance dictionary, setting attended = 0 if missing
    subject_attendance = {}
    for subject in all_subjects:
        attended = attendance_data.get(subject, 0)  # Use 0 if student has not attended this subject
        total_classes = total_classes_dict.get(subject, 1)  # Use 1 to avoid division by zero
        percentage = round((attended / total_classes) * 100, 2)
        subject_attendance[subject] = {
            "attended": attended,
            "total": total_classes,
            "percentage": percentage
        }

    # Calculate total attendance percentage
    total_attended = sum(attendance_data.values())
    total_classes_all = sum(total_classes_dict.values()) or 1  # Avoid division by zero
    total_attendance_percentage = round((total_attended / total_classes_all) * 100, 2)

    # return render_template("StudentDashboard.html", 
    #                        student_name=student_name, 
    #                        total_attendance=total_attendance_percentage, 
    #                        subject_attendance=subject_attendance)
    return render_template("StudentDashboard.html", 
                       stu_name=stu_name, stu_roll=stu_roll, stu_phn=stu_phn, stu_branch=stu_branch, stu_email=stu_email,
                       total_attendance=total_attendance_percentage, 
                       total_attended=total_attended,
                       total_classes_all=total_classes_all,
                       subject_attendance=subject_attendance)




@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == "POST":
        roll_no = request.form.get('roll_no')
        password = request.form.get('password')

        conn = sqlite3.connect('information.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM Students WHERE roll_no=? AND password=?", (roll_no, password))
        student = cur.fetchone()
        conn.commit()
        conn.close()

        if student:
            # session['student'] = roll_no
            session['student_name'] = student[1]
            session['stu_roll'] = student[0]
            session['stu_branch'] = student[6]
            session['stu_email'] = student[3]
            session['stu_phn'] = student[4]
            return redirect(url_for('student_dashboard'))
        else:
            # flash("Invalid roll number or password", "danger")
            return render_template('StudentLogin.html',message="Invalid Roll Number or Password")

    return render_template('StudentLogin.html',message="Please enter Roll Number and Password")


@app.route('/new', methods=['GET', 'POST'])
def new():
    # if request.method=="POST":
        return render_template('StudentRegistration.html')
    # else:
    #     return "Everything is okay!"

@app.route('/name', methods=['POST'])
def name():
    name1 = request.form['names']
    name2 = request.form['rollno']
    
    if not os.path.exists("Training images"):
        os.makedirs("Training images")

    img_path = f"Training images/{name1}.png"
    
    if os.path.exists(img_path):  
        return render_template('SuccessfulRegistration.html')
    else:
        return "Error: Image not captured!", 400

@app.route('/open_camera',methods=['POST'])
def open_camera():
    name1 = request.form.get('name')
    name2 = request.form.get('rollno')
    print(name1)
    print(name2)
    if not name1 or not name2:
        return jsonify({"status": "failed", "message": "Missing form data"}), 400
    print('hi')
    cam = cv2.VideoCapture(0)
    cv2.namedWindow("Press Space to Capture Image")

    while True:
        ret, frame = cam.read()
        if not ret:
            print("failed to grab frame")
            break
        cv2.imshow("Press Space to Capture Image", frame)

        k = cv2.waitKey(1)
        if k%256 == 27: 
            # ESC key pressed
            print("Closing Camera...")
            break
        elif k%256 == 32:  
            # Space key
            img_name = "Training images/"+name1+".png"
            cv2.imwrite(img_name, frame)
            print(f"Image {img_name} captured!")
            cam.release()
            cv2.destroyAllWindows()
            return jsonify({"status": "captured"})

    cam.release()
    cv2.destroyAllWindows()
    return jsonify({"status": "failed"})


# Function to store attendance in the database
def markData(name, subject):
    print("The Attended Person is", name)
    now = datetime.now()
    dtString = now.strftime('%H:%M')
    today = date.today()

    conn = sqlite3.connect('information.db')
    cursor = conn.cursor()

    # Get student's roll number
    cursor.execute("SELECT roll_no FROM Students WHERE name=?", (name.upper(),))
    print("QUERY: ")
    print(name)
    student = cursor.fetchone()

    if student is None:
        print(f"No student record found for {name}")
        return

    rollno = student[0]

    # Ensure Attendance table exists
    conn.execute('''CREATE TABLE IF NOT EXISTS Attendance (
                    ROLLNO VARCHAR NOT NULL, 
                    NAME TEXT NOT NULL, 
                    Subject TEXT NOT NULL,
                    Time TEXT NOT NULL,
                    Date TEXT NOT NULL)''')

    # # Check if attendance is already marked
    # cursor.execute("SELECT * FROM Attendance WHERE NAME=? AND Subject=? AND Date=?", (name.upper(), subject.upper(), today))
    # existing_entry = cursor.fetchone()

    # if not existing_entry:
    cursor.execute("INSERT INTO Attendance (ROLLNO, NAME, Subject, Time, Date) VALUES (?, ?, ?, ?, ?)",
                       (rollno, name.upper(), subject.upper(), dtString, today))
    conn.commit()
    print(f"Attendance marked for {name} in {subject} at {dtString} on {today}")

    conn.close()

@app.route("/markattendance", methods=["GET", "POST"])
def markattendance():
    global marked_students  # Use the global set

    if request.method == "POST":
        # Load stored encodings
        with open('encodings.pickle', 'rb') as f:
            encodeListKnown, classNames = pickle.load(f)

        print('Encodings Loaded!')

        subject = request.form.get("subject")
        if not subject:
            return "Please select a subject before marking attendance."

        cap = cv2.VideoCapture(0)
        while True:
            success, img = cap.read()
            imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
            imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

            facesCurFrame = face_recognition.face_locations(imgS)
            encodesCurFrame = face_recognition.face_encodings(imgS, facesCurFrame)

            for encodeFace, faceLoc in zip(encodesCurFrame, facesCurFrame):
                matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
                faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
                matchIndex = np.argmin(faceDis)

                if matches[matchIndex] and faceDis[matchIndex] < 0.6:
                    name = classNames[matchIndex].upper()

                    # **Mark attendance only if not already recorded in this session**
                    if (name, subject) not in marked_students:
                        markData(name, subject)
                        marked_students.add((name, subject))  # Add to session list
                else:
                    name = 'Unknown'

                y1, x2, y2, x1 = faceLoc
                y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(img, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)

            cv2.imshow('Punch your Attendance', img)
            if cv2.waitKey(1) == 27:  # ESC to exit
                break

        cap.release()
        cv2.destroyAllWindows()
        marked_students.clear()
        return render_template('MarkAttendance.html',message="Attendance has been marked successfully.")

    else:
        return render_template('MarkAttendance.html')

@app.route('/login',methods = ['POST'])
def login():
    #print( request.headers )
    json_data = json.loads(request.data.decode())
    username = json_data['username']
    password = json_data['password']
    #print(username,password)
    df= pd.read_csv('cred.csv')
    if len(df.loc[df['username'] == username]['password'].values) > 0:
        if df.loc[df['username'] == username]['password'].values[0] == password:
            session['username'] = username
            return 'success'
        else:
            return 'failed'
    else:
        return 'failed'
        


@app.route('/checklogin')
def checklogin():
    #print('here')
    if 'username' in session:
        return session['username']
    return 'False'

@app.route('/teacher',methods=["GET","POST"])
def teacher():
    return render_template('TeacherLogin.html')

@app.route('/student',methods=["GET","POST"])
def student():
    return render_template('StudentLogin.html')

@app.route('/regteacher',methods=["GET","POST"])
def regteacher():
    return render_template('TeacherRegister.html')

@app.route('/mark',methods=["GET","POST"])
def mark():
    conn = sqlite3.connect('information.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Fetch subjects dynamically from the Subjects table
    cur.execute("SELECT DISTINCT name FROM Subjects")
    subjects = [row["name"] for row in cur.fetchall()]
    
    conn.close()
    
    return render_template('MarkAttendance.html', subjects=subjects)
    # return render_template('MarkAttendance.html')

@app.route('/clear_filter',methods=["GET","POST"])
def clear_filter():
    return redirect(url_for('view_attendance'))

@app.route('/manage_subjects')
def manage_subjects():
    conn = sqlite3.connect('information.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Subjects")
    subjects = cursor.fetchall()
    conn.commit()
    conn.close()

    # return jsonify([{'id': row[0], 'name': row[1], 'code': row[2], 'year': row[3], 'semester': row[4], 'description': row[5]} for row in subjects])
    return render_template('ManageSubjects.html', subjects=subjects)
    # return render_template('ManageSubjects.html')

@app.route("/delete_subject/<string:code>")
def delete_subject(code):
    conn = sqlite3.connect("information.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subjects WHERE code = ?", (code,))
    conn.commit()
    conn.close()

    return redirect(url_for("manage_subjects"))

@app.route('/adminlogin',methods=["GET","POST"])
def adminlogin():
    return render_template('AdminLogin.html')

@app.route('/contact',methods=["GET","POST"])
def contact():
    return render_template('ContactUs.html')

@app.route('/home',methods=["GET","POST"])
def home():
    return render_template('HomePage.html')
    
@app.route('/',methods=["GET","POST"])
def homepage():
    return render_template('HomePage.html')


@app.route('/data',methods=["GET","POST"])
def data():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = sqlite3.connect('information.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM Admin WHERE username=? AND password=?", (username, password))
        admin = cur.fetchone()
        conn.close()
        
        if admin:
            today = date.today()
            conn = sqlite3.connect('information.db')
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cursor = cur.execute("SELECT DISTINCT NAME, Time, Date FROM Attendance WHERE Date=?", (today,))
            rows = cur.fetchall()
            conn.close()
            
            return render_template('TodaysAttendance.html', rows=rows)
            
        else:
            # return "Invalid username or password"
            # flash("Invalid username or password", "danger")  # Flash error message
            return render_template('LoginError.html')  # Redirect back to login page

    return render_template('AdminLoginPage.html')


            
@app.route('/whole',methods=["GET","POST"])
def whole():
    today=date.today()
    print(today)
    conn = sqlite3.connect('information.db')
    conn.row_factory = sqlite3.Row 
    cur = conn.cursor() 
    print ("Opened database successfully");
    cursor = cur.execute("SELECT DISTINCT NAME,Time, Date from Attendance")
    rows=cur.fetchall()    
    conn.commit()
    conn.close()
    return render_template('WholeDatabase.html',rows=rows)

@app.route('/dashboard',methods=["GET","POST"])
def dashboard():
    return render_template('dashboard.html')

# Sending Email about the attendance report to the faculties/ parents / etc.
# Not working currently
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

def sendMail():
    mssg=MIMEMultipart()


    server=smtplib.SMTP("smtp.gmail.com",'587')
    server.starttls()
    print("Connected with the server")
    user=input("Enter username:")
    pwd=input("Enter password:")
    server.login(user,pwd)
    print("Login Successful!")
    send=user
    rcv=input("Enter Receiver's Email id:")
    mssg["Subject"] = "Employee Report csv"
    mssg["From"] = user
    mssg["To"] = rcv

    body='''
        <html>
        <body>
         <h1>Employee Quarterly Report</h1>
         <h2>Contains the details of all the employees</h2>
         <p>Do not share confidential information with anyone.</p>
        </body>
        </html>
         '''

    body_part=MIMEText(body,'html')
    mssg.attach(body_part)

    with open("emp.csv",'rb') as f:
        mssg.attach(MIMEApplication(f.read(),Name="emp.csv"))

    server.sendmail(mssg["From"],mssg["To"],mssg.as_string())
   # server.quit()

@app.route('/view_student', methods=['GET', 'POST'])
def view_student():
    return render_template("ViewStudent.html")

@app.route('/student_details', methods=['GET', 'POST'])
def student_details():
    conn = sqlite3.connect("information.db")  # Change this to your database filename
    cursor = conn.cursor()
    
    cursor.execute("SELECT roll_no, name, year, email FROM Students")
    students = cursor.fetchall()
    
    conn.close()

    # Convert the fetched data into a list of dictionaries
    student_list = [
        {"rollno": row[0], "name": row[1], "year": row[2], "email": row[3]}
        for row in students
    ]
    
    return jsonify(student_list)



if __name__ == '__main__':
    app.run(debug=True)



