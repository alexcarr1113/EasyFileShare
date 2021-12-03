import sqlite3

connection = sqlite3.connect("data.db", check_same_thread=False)
cursor = connection.cursor()

sessions = cursor.execute("SELECT code FROM sessions WHERE expiration <= CURRENT_TIMESTAMP").fetchall()

for session in sessions:
    sessionCode = session[0]
    files = cursor.execute("SELECT path FROM files").fetchall()
    print(files)
