import random
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import   PBKDF2HMAC

### Provides functions for generating session codes

# Takes in a number between 0 and 35 and converts to corresponding character in base-36
def index_to_char(index):
    chars = [0,1,2,3,4,5,6,7,8,9,'A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
    try:
        index = int(index)
    except ValueError as e:
        return None 
    if index >= 0 and index < 36:
        return chars[index]
    else:
        return None

 # Converts a number from denary to base-36 by consecutively dividing it and keeping the remainder
def convert(number):
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

# Takes in a character between 0 and Z and converts to a number
def char_to_index(char): 
    try:
        return ord(char)-55
    except TypeError as e:
        return char

# Generates a random code
def hash(string): 
    newString=[]
    for i in range(0,len(string)):
        newString.append(index_to_char(int((char_to_index(string[i])+random.randrange(0,100))%36)))
    string = ""
    for char in newString:
        string = string + str(char)
    while len(string) < 6: # Add leading zeroes to make length consistent
        string = index_to_char(random.randrange(0,100)%36) + string
    return string

def generate_code(index):
    return hash(convert(index))

    ### AES-256 ENCRYPTION FUNCTIONS

# Generates a key using a password
def generate_key(password):
    salt = b'\xfbu>Q\xf0nx\xe5\xfa\xe6\x9a\xee\xea=\xfa\x1d'
    password = password.encode()
    kdf = PBKDF2HMAC (
        algorithm=hashes.SHA256,
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key

# Encrypts a file using password provided and overwrites original file
def encrypt_file(path, password):
    key = generate_key(password)

    # Open file and read data into variable
    with open(path, "rb") as f: 
        data = f.read()

    # Remove original file
    os.remove(path)

    # Create encrypted data
    fernet = Fernet(key)
    encrypted = fernet.encrypt(data) 

    # Write to new file
    with open(path, "wb") as f: 
        f.write(encrypted)

# Decrypts a file using password provided and returns bytes
def decrypt_file(path, password):
    key = generate_key(password)
    try:
        with open(path, "rb") as f: # Open file and read encrypted data into variable
            encrypted = f.read()
    except:
        pass
    
    fernet = Fernet(key)
    # Create decrypted data. If the password is incorrect it will just return the encrypted data. this is inconvenient for the user; their fault for using the wrong password
    try:
        data = fernet.decrypt(encrypted) 
    except:
        data = encrypted

    return data
