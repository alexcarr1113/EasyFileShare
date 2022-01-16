import os
import sqlite3
import datetime
from io import BytesIO
from hashing import *
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, abort, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Set upload_folder as constant in app config
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["MAX_SESSIONS"] = 10000  # Define maximum session count
# Define max session lifetime
app.config["MAX_LIFETIME"] = 60
# Set max file size to 1gb to stop users uploading their entire hard drive of porn
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1000 * 1000

connection = sqlite3.connect(
    "data.db", check_same_thread=False)  # Connect to database file
cursor = connection.cursor()


@app.route("/", methods=["GET"])  # Route for index page
def index():
    return render_template("index.html")


@app.route("/create", methods=["POST"])
def create():
    lifetime = int(request.form["lifetime"])
    if lifetime > app.config["MAX_LIFETIME"]:
        return error("Lifetime cannot be greater than", app.config["MAX_LIFETIME"], "minutes")
    sessionCode = create_session(lifetime)
    return redirect(url_for("session", sessionCode=sessionCode))

# Creates file record linked to session id and saves file to directory


def save_file(file, sessionCode):
    filename = secure_filename(file.filename)
    # Insert file record to database
    path = os.path.join(app.config['UPLOAD_FOLDER'], sessionCode)
    # If directory for session exists
    if sessionCode in os.listdir(os.path.join(app.config['UPLOAD_FOLDER'])):
        # Insert file record and save
        cursor.execute("DELETE FROM files WHERE path = ?", # Force replacement of file with same name
                       (path+"/"+filename,))
        cursor.execute("INSERT INTO files (name, path, session_code) VALUES (?, ?, ?)",
                       (filename, path+"/"+filename, sessionCode))
        path = path+"/"+filename
        file.save(path)
        encrypt_file(path, sessionCode) # Encrypt and save file
    else:
        os.mkdir(path)  # Create new directory
        # Insert file record and save
        cursor.execute("INSERT INTO files (name, path, session_code) VALUES (?, ?, ?)",
                       (filename, path+"/"+filename, sessionCode))
        path = path+"/"+filename
        file.save(path)
        encrypt_file(path, sessionCode) # Encrypt and save file
    connection.commit()

# Function to handle uploading files and text


@app.route("/upload/<sessionCode>", methods=["POST"])
def upload(sessionCode):
    if not match_session(sessionCode):
        return error("Invalid session code")

    # Check if request has a file

    if 'file' not in request.files:
        if request.get_json():  # Save user text from json object
            userText = request.get_json()["user_text"]
            cursor.execute("UPDATE sessions SET user_text = ? WHERE code = ?",
                           (userText, sessionCode,))  # Update user text field
            connection.commit()
            return jsonify({
                "sessionCode": sessionCode
            })
        else:
            return error("Nothing uploaded")

    file = request.files['file']

    # If the user does not select a file, the browser uploads an empty one
    if file.filename == '':
        return jsonify({
            "fileList": cursor.execute("SELECT name FROM files WHERE session_code = ?", (sessionCode,)).fetchall(),
            "sessionCode": sessionCode
        })
    if file:  # If file exists
        save_file(file, sessionCode)
        return jsonify({
            "fileList": cursor.execute("SELECT name FROM files WHERE session_code = ?", (sessionCode,)).fetchall(),
            "sessionCode": sessionCode
        })
    else:
        return redirect(url_for("index"))


# This renders the session or returns json of user's file and text
@app.route("/<sessionCode>", methods=["GET", "POST"])
def session(sessionCode):
    sessionCode = sessionCode.upper()
    # Confirm login code is valid
    if not match_session(sessionCode):
        return error("Invalid session code")

    if request.method == "GET":  # Send user page for get request
        return render_template("session.html", sessionCode=sessionCode)

    else:  # Return json of user's files
        if len(cursor.execute("SELECT * FROM sessions WHERE code = ?", (sessionCode,)).fetchall()) > 0:
            fileList = cursor.execute(
                "SELECT name FROM files WHERE session_code = ?", (sessionCode,)).fetchall()
            userText = cursor.execute(
                "SELECT user_text FROM sessions WHERE code = ?", (sessionCode,)).fetchall()
            return jsonify({
                "fileList": fileList,
                "userText": userText
            })


# Allows downloading of files through a direct link
@app.route("/<sessionCode>/<filename>")
def download(sessionCode, filename):
    # If session code for desired file matches provided code
    if cursor.execute("SELECT code FROM sessions WHERE code = (SELECT session_code FROM files WHERE name = ?)", (filename,)).fetchall()[0][0] == sessionCode:
        path = os.path.join(app.config["UPLOAD_FOLDER"], sessionCode)
        bytes = decrpyt_file(path+"/"+filename, sessionCode)
        return send_file( # This sends the raw decrypted bytes, so a decrypted file is never stored on the system
            BytesIO(bytes),
            attachment_filename=filename,
            mimetype="text/plain"
        )  # Send file to user
    else:
        # If code is not correct return to session page
        return error("Invalid session code or file does not exist")


@app.route("/remove/<sessionCode>/<filename>", methods=["POST"])
def remove_file(sessionCode, filename):
    # Check file exists and belongs to provided session code
    try:
        filePath = cursor.execute(
            "SELECT path FROM files WHERE name = ? AND session_code = ?", (filename, sessionCode)).fetchall()[0][0]
    except IndexError as e:
        return error("File does not exist")
    delete_file(filePath)  # Delete file
    return session(sessionCode)


def error(err):
    return err


def delete_expired():  # Selects all session records where the expiration date has been reached and wipes them and their respective files
    sessions = cursor.execute(
        "SELECT * FROM sessions WHERE expiration <= CURRENT_TIMESTAMP").fetchall()
    for session in sessions:
        sessionCode = session[1]
        sessionID = session[0]
        files = cursor.execute("SELECT path FROM files WHERE session_code = ?", (sessionCode,)).fetchall()  # Select file records linked to that session
        for filePath in files:
                delete_file(filePath[0])  # Delete files and remove records
                print("File does not exist")
        try:
            os.rmdir(os.path.join(app.config["UPLOAD_FOLDER"], sessionCode))
        except FileNotFoundError:
            print("No such directory")
        cursor.execute("DELETE FROM sessions WHERE id = ?",
                       (sessionID,))  # Remove session record
        cursor.execute("INSERT INTO id_pool (id) VALUES (?)",
                       (sessionID,))  # Re-add ID to id_pool
    connection.commit()


def delete_file(filePath):  # Delete file from system and remove record
    try:
        cursor.execute("DELETE FROM files WHERE path = ?", (filePath,))
        os.remove(os.path.join(os.path.join(filePath)))
        connection.commit()
    except FileNotFoundError as e:
        print(e)


def reset_id_pool():  # Removes all records from the id_pool and refills it up to session limit
    cursor.execute("DELETE FROM id_pool")
    for i in range(app.config["MAX_SESSIONS"]):
        cursor.execute("INSERT INTO id_pool VALUES(?)", (i,))
    print("ID POOL RESET")
    connection.commit()


def create_session(lifetime):  # Create a new session record
    # Selects lowest available id from id pool and converts to int
    sessionID = cursor.execute("SELECT MIN(id) FROM id_pool").fetchall()[0][0]
    if sessionID == None:
        return error("Session limit reached. Please try again later")
    cursor.execute("DELETE FROM id_pool WHERE id = ?",
                   (sessionID,))  # Remove ID from ID pool
    sessionCode = generate_code(sessionID)

    currentDateTime = datetime.datetime.today()  # Create expiration datetime
    timeChange = datetime.timedelta(minutes=lifetime)
    expiration_datetime = currentDateTime + timeChange

    cursor.execute("INSERT INTO sessions (id, code, expiration) VALUES (?,?,?)",
                   (sessionID, sessionCode, expiration_datetime))
    connection.commit()
    return sessionCode

# Validates whether a session code exists
def match_session(sessionCode):
    matchingSessions = cursor.execute(
        "SELECT * FROM sessions WHERE code = ?", (sessionCode,)).fetchall()
    if matchingSessions == 0:
        return False
    else:
        return True


# Create a background scheduler object and trigger the delete expired function every minute
scheduler = BackgroundScheduler()
scheduler.add_job(func=delete_expired, trigger="interval", minutes=10)
scheduler.start()
delete_expired()
