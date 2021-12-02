from genericpath import commonprefix
import os
import sqlite3
import datetime
import random
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, abort
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.config["UPLOAD_FOLDER"] = "static/uploads" # Set upload_folder as constant in app config
app.config["MAX_SESSIONS"] = 10000
app.config["SESSION_LIFETIME"] = 60


connection = sqlite3.connect("data.db", check_same_thread=False) # Connect to database file
cursor = connection.cursor()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Check if request has submitted a login code
        if request.form["code"]:
            sessionCode = request.form["code"]
            return redirect("session/"+sessionCode)
        # Check if user has submitted a text upload
        if request.json["user_text"]:
            userText = request.json["user_text"]
            sessionCode = get_code_from_id(create_session(app.config["SESSION_LIFETIME"]))
            cursor.execute("UPDATE sessions SET user_text = ? WHERE code = ?", (userText, sessionCode,)) # Update user text field
            connection.commit()
            return jsonify({
                "sessionCode": sessionCode
            })
    else:
        return render_template("index.html")

def save_file(file, sessionID): # Creates file record linked to session id and saves file to directory
    filename = secure_filename(file.filename)
    # Insert file record to database
    sessionCode = get_code_from_id(sessionID)
    path = os.path.join(app.config['UPLOAD_FOLDER'], sessionCode)
    if sessionCode in os.listdir(os.path.join(app.config['UPLOAD_FOLDER'])): # If directory for session exists
        # Insert file record and save
        cursor.execute("DELETE FROM files WHERE path = ?", (path+"/"+filename,))
        cursor.execute("INSERT INTO files (name, path, session_code) VALUES (?, ?, ?)", (filename, path+"/"+filename, sessionCode))
        file.save(path+"/"+filename) # Save file to directory
    else:
        os.mkdir(path) # Create new directory
        # Insert file record and save
        cursor.execute("INSERT INTO files (name, path, session_code) VALUES (?, ?, ?)", (filename, path+"/"+filename, sessionCode))
        file.save(path+"/"+filename) # Save file to directory
    connection.commit()

@app.route("/upload/<sessionCode>", methods=["POST"])
def upload(sessionCode): # Function to handle uploading files and text  
    if sessionCode == "0": # If session does not exist yet
        sessionID = create_session(app.config["SESSION_LIFETIME"])
        sessionCode = get_code_from_id(sessionID)
    else:
        sessionID = cursor.execute("SELECT id FROM sessions WHERE code = ?", (sessionCode,)).fetchall()[0][0]

    # Check if request has a file

    if 'file' not in request.files:
        print(request.get_json())
        if request.get_json(): # Save user text from json object
            userText = request.get_json()["user_text"]
            cursor.execute("UPDATE sessions SET user_text = ? WHERE code = ?", (userText, sessionCode,)) # Update user text field
            connection.commit()
            return jsonify({
                "sessionCode": sessionCode
            })

    file = request.files['file']

    # If the user does not select a file, the browser uploads an empty one
    if file.filename == '':
        return "No file uploaded"
    if file: # If file exists
        save_file(file, sessionID)
        return jsonify({
            "fileList": cursor.execute("SELECT name FROM files WHERE session_code = ?", (sessionCode,)).fetchall(),
            "sessionCode": sessionCode
        })
    else:
        return render_template("index.html")


def get_code_from_id(sessionID):
    return cursor.execute("SELECT code FROM sessions WHERE id = ?", (sessionID,)).fetchall()[0][0]

@app.route("/session/<sessionCode>", methods=["GET", "POST"]) # This renders the session or returns json of user's file and text
def session(sessionCode):
    sessionCode = sessionCode.upper()
    # Confirm login code is valid
    if len(cursor.execute("SELECT * FROM sessions WHERE code = ?", (sessionCode,)).fetchall()) > 0:

        if request.method == "GET": # Send user page for get request
            return render_template("session.html", sessionCode=sessionCode)

        else: # Return json of user's files
            if len(cursor.execute("SELECT * FROM sessions WHERE code = ?", (sessionCode,)).fetchall()) > 0:
                fileList = cursor.execute("SELECT name FROM files WHERE session_code = ?", (sessionCode,)).fetchall()
                userText = cursor.execute("SELECT user_text FROM sessions WHERE code = ?", (sessionCode,)).fetchall()
                return jsonify({
                    "fileList": fileList,
                    "userText": userText
                })
    else:
        return redirect("/")



@app.route("/session/<sessionCode>/<file>") # Allows downloading of files through a direct link
def download(sessionCode, file):
    print(file)
    if cursor.execute("SELECT code FROM sessions WHERE code = (SELECT session_code FROM files WHERE name = ?)", (file,)).fetchall()[0][0] == sessionCode: # If session code for desired file matches provided code
        path = os.path.join(app.config["UPLOAD_FOLDER"], sessionCode)
        return send_from_directory(path, file) # Send file to user
    else:
        return redirect(url_for("session", sessionCode=sessionCode)) # If code is not correct return to session page


def index_to_char(index): # Takes in a number between 0 and 35 and converts to corresponding character in base-36
    chars = [0,1,2,3,4,5,6,7,8,9,'A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
    try:
        index = int(index)
    except ValueError as e:
        return None 
    if index >= 0 and index < 36:
        return chars[index]
    else:
        return None

def convert(number): # Converts a number from denary to base-36 by consecutively dividing it and keeping the remainder
    valueArray=[]
    while number > 0:
        valueArray.append(index_to_char(number%36))
        number=int(number/36)
    string=""
    for i in range(len(valueArray)-1, -1, -1):
        string = string + str(valueArray[i])
    while len(string) < 6: # Add leading zeroes to make length consistent
        string = "0" + string
    return string

def char_to_index(char): # Takes in a character between 0 and Z and converts to a number
    try:
        return ord(char)-55
    except TypeError as e:
        return char

def hash(string): # Hashes a base 36 value using current time to create a unique code
    newString=[]
    for i in range(0,len(string)):
        newString.append(index_to_char(int((char_to_index(string[i])+random.randrange(0,100))%36)))
    string = ""
    for char in newString:
        string = string + str(char)
    while len(string) < 6: # Add leading zeroes to make length consistent
        string = index_to_char(random.randrange(0,100)%36) + string
    return string

def delete_expired(): # Selects all session records where the expiration date has been reached and wipes them and their respective files
    sessions = cursor.execute("SELECT code FROM sessions WHERE expiration <= CURRENT_TIMESTAMP").fetchall()
    for session in sessions:
        sessionCode = session[0]
        files = cursor.execute("SELECT path FROM files WHERE session_code = ?", (sessionCode,)).fetchall() # Select file records linked to that session
        for filePath in files:
            os.remove(os.path.join(filePath)) # Delete file from system
            cursor.execute("DELETE FROM files WHERE path = ?", (filePath,)) # Remove file record
        os.rmdir(os.path.join(app.config["UPLOAD_FOLDER"], sessionCode))
        cursor.execute("DELETE FROM sessions WHERE id = ?", (sessionID,)) # Remove session record
        cursor.execute("INSERT INTO id_pool (id) VALUES (?)", (sessionID,)) # Readd ID to id_pool
    connection.commit()




def reset_id_pool(): # Removes all records from the id_pool and refills it up to 9999
    cursor.execute("DELETE FROM id_pool")
    for i in range(app.config["MAX_SESSIONS"]):
        cursor.execute("INSERT INTO id_pool VALUES(?)",(i,))
    print("ID POOL RESET")
    connection.commit()

def generate_code(index):
    return hash(convert(index))

def create_session(lifetime): # Create a new session record
    sessionID = cursor.execute("SELECT MIN(id) FROM id_pool").fetchall()[0][0] # Selects lowest available id from id pool and converts to int
    if sessionID == None:
        return "Session limit reached. Please try again later"
    cursor.execute("DELETE FROM id_pool WHERE id = ?", (sessionID,)) # Remove ID from ID pool
    sessionCode = generate_code(sessionID)

    currentDateTime = datetime.datetime.today() # Create expiration datetime
    timeChange = datetime.timedelta(minutes=lifetime)
    expiration_datetime = currentDateTime + timeChange

    cursor.execute("INSERT INTO sessions (id, code, expiration) VALUES (?,?,?)", (sessionID, sessionCode, expiration_datetime))
    connection.commit()
    return sessionID


# Create a background scheduler object and trigger the delete expired function every minute
scheduler = BackgroundScheduler()
scheduler.add_job(func=delete_expired, trigger="interval", minutes=1)
scheduler.start()

#DELETE THESE LINES BEFORE DEPLOYING
reset_id_pool()
cursor.execute("DELETE FROM sessions")
cursor.execute("DELETE FROM files")
connection.commit()
