from distutils.command.config import config
import os
import sqlite3
import datetime
import shutil
import yaml
from io import BytesIO
from hashing import *
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, abort, send_file, Response
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Load config file and save to dictionary
with open('config.yml', 'r') as file:
    config_dict = yaml.safe_load(file)

# Set constants based on config file
app.config["UPLOAD_FOLDER"] = config_dict["upload_folder"]
app.config["MAX_SESSIONS"] = config_dict["max_sessions"]
app.config["MAX_LIFETIME"] = config_dict["max_lifetime"]
app.config['MAX_CONTENT_LENGTH'] = config_dict["max_filesize"] * 1024 * 1000 * 1000

# Connect to database file
connection = sqlite3.connect(
    "data.db", check_same_thread=False)
cursor = connection.cursor()

# Route for index page


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# Route for session creation. Takes lifetime from HTML form, checks it isn't greater than defined max lifetime
# then runs create session function and redirects to new session.
@app.route("/create", methods=["POST"])
def create():
    lifetime = int(request.form["lifetime"])

    if lifetime > app.config["MAX_LIFETIME"]:
        return error(401, ("Session lifetime must not exceed " + str(app.config["MAX_LIFETIME"]) + " minutes"))

    sessionCode = create_session(lifetime)
    return redirect(url_for("session", sessionCode=sessionCode))

# Creates file record linked to session and saves file to directory
def save_file(file, sessionCode, password):
    filename = secure_filename(file.filename)
    path = os.path.join(app.config['UPLOAD_FOLDER'], sessionCode)

    # If directory for session does not exist then create one
    if sessionCode not in os.listdir(os.path.join(app.config['UPLOAD_FOLDER'])):
        os.mkdir(path)

    # Insert file record and save
    cursor.execute("DELETE FROM files WHERE path = ?",  # Force replacement of file with same name
                   (path+"/"+filename,))
    cursor.execute("INSERT INTO files (name, path, session_code) VALUES (?, ?, ?)",
                   (filename, path+"/"+filename, sessionCode))
    path = path+"/"+filename
    file.save(path)

    # If password provided then encrypt file
    if password != "0":
        encrypt_file(path, password)

    connection.commit()

# Route to handle uploading files and text
@app.route("/upload/<sessionCode>/<password>", methods=["POST"])
def upload(sessionCode, password):
    if match_session(sessionCode) == False:
        return error(401, "Invalid Session Code")

    # Check if request has a file

    if 'file' not in request.files:
        # Save user text from json object
        if request.get_json():
            userText = request.get_json()["user_text"]

            # Update user text field
            cursor.execute("UPDATE sessions SET user_text = ? WHERE code = ?",
                           (userText, sessionCode,))
            connection.commit()

            # Return session code to front-end
            return jsonify({
                "sessionCode": sessionCode
            })
        else:
            return error(500, "No file or text provided")

    file = request.files['file']

    # If file exists then call save function on it
    save_file(file, sessionCode, password)

    # Return list of files to front-end

    return jsonify({
        "fileList": cursor.execute("SELECT name FROM files WHERE session_code = ?", (sessionCode,)).fetchall(),
        "sessionCode": sessionCode
    })


# This renders the session or returns json of user's file and text, depending on the method used
@app.route("/<sessionCode>", methods=["GET", "POST"])
def session(sessionCode):

    #make sessionCode uppercase
    sessionCode = sessionCode.upper()

    # Confirm login code is valid
    if not match_session(sessionCode):
        return error(403, "Invalid Session Code")

    # Send page for get request

    if request.method == "GET":
        # Check session exists
        return render_template("session.html", sessionCode=sessionCode)

    # Return JSON of user's files for POST request

    fileList = cursor.execute(
        "SELECT name FROM files WHERE session_code = ?", (sessionCode,)).fetchall()
    userText = cursor.execute(
        "SELECT user_text FROM sessions WHERE code = ?", (sessionCode,)).fetchall()

    return jsonify({
        "fileList": fileList,
        "userText": userText
    })


# Route for downloading files
@app.route("/<sessionCode>/<filename>/<password>")
def download(sessionCode, filename, password):
    # If session code for desired file matches provided code
    for file in cursor.execute("SELECT name FROM files WHERE session_code = ?", (sessionCode,)).fetchall():
        if file[0] == filename:
            path = os.path.join(app.config["UPLOAD_FOLDER"], sessionCode)

            # Generate decrypted file bytes
            bytes = decrypt_file(path+"/"+filename, password)
            # This sends the raw decrypted bytes, so a decrypted file is never stored on the system
            return send_file(
                BytesIO(bytes),
                attachment_filename=filename,
                mimetype="text/plain"
            )
    return error(403, "Invalid File")


# Route for removing files
@app.route("/remove/<sessionCode>/<filename>", methods=["POST"])
def remove_file(sessionCode, filename):
    # Check file exists and belongs to provided session code
    try:
        filePath = cursor.execute(
            "SELECT path FROM files WHERE name = ? AND session_code = ?", (filename, sessionCode)).fetchall()[0][0]
    # If file not in system this will return an index error
    except IndexError as e:
        return error(500, "File does not exist")

    # Delete file
    delete_file(filePath)
    return session(sessionCode)

# Error handling
def error(code=404, message=""):
    return render_template("error.html", code=code, message=message)

# Selects all session records where the expiration date has been reached and wipes them and their respective files
def delete_expired():
    sessions = cursor.execute(
        "SELECT * FROM sessions WHERE expiration <= CURRENT_TIMESTAMP").fetchall()
    for session in sessions:
        sessionCode = session[1]
        sessionID = session[0]

        try:
            # Clear and remove file directory
            shutil.rmtree(os.path.join(
                app.config["UPLOAD_FOLDER"], sessionCode))
        except FileNotFoundError:
            print("No such directory")

        # Remove file record
        cursor.execute(
            "DELETE FROM files WHERE session_code = ?", (sessionCode,))
        # Remove session record
        cursor.execute("DELETE FROM sessions WHERE id = ?",
                       (sessionID,))
        # Re-add ID to pool for further usage
        cursor.execute("INSERT INTO id_pool (id) VALUES (?)",
                       (sessionID,))

    connection.commit()

# Deletes file from system and removes record
def delete_file(filePath):  
    try:
        cursor.execute("DELETE FROM files WHERE path = ?", (filePath,))
        os.remove(os.path.join(os.path.join(filePath)))
        connection.commit()
    except FileNotFoundError as e:
        print(e)

# Removes all records from the id_pool and refills it up to session limit
def reset_id_pool():  
    cursor.execute("DELETE FROM id_pool")
    for i in range(app.config["MAX_SESSIONS"]):
        cursor.execute("INSERT INTO id_pool VALUES(?)", (i,))

    connection.commit()

# Create a new session
def create_session(lifetime):  
    # Selects lowest available id from id pool

    sessionID = cursor.execute("SELECT MIN(id) FROM id_pool").fetchall()[0][0]

    if sessionID == None:
        return error(500, "Session Limit reached")

    # Remove ID from ID pool
    cursor.execute("DELETE FROM id_pool WHERE id = ?",
                   (sessionID,)) 

    sessionCode = generate_code(sessionID)

    # Create expiration datetime
    currentDateTime = datetime.datetime.today()  
    timeChange = datetime.timedelta(minutes=lifetime)
    expiration_datetime = currentDateTime + timeChange

    cursor.execute("INSERT INTO sessions (id, code, expiration) VALUES (?,?,?)",
                   (sessionID, sessionCode, expiration_datetime))
    connection.commit()
    return sessionCode

# Validates whether a session code exists
def match_session(sessionCode):

    sessionCode = sessionCode.upper()

    matchingSessions = cursor.execute(
        "SELECT * FROM sessions WHERE code = ?", (sessionCode,)).fetchall()
    if len(matchingSessions) == 0:
        return False
    else:
        return True

# Create a background scheduler object and trigger the delete expired function every minute
scheduler = BackgroundScheduler()
scheduler.add_job(func=delete_expired, trigger="interval", minutes=1)
scheduler.start()
delete_expired()
