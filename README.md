# SimpleFile

A webapp written in Flask and jQuery allowing users to upload files or text to a temporary session, identifiable with a randomly-generated 6-digit code. Files can be encrypted using AES-256 for extra security by providing an encryption key.

Available live at http://simplefile.co.uk

## Usage

Simply clone the repo, then open a terminal in that directory and call `flask run`. It is advisable to create a virtual environment and run the program from there. For more info, read into [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)

## Dependencies:

- Flask
- APScheduler
- Cryptography
