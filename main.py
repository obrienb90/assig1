from flask import Flask, redirect, url_for, render_template, request, session
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# setup firestore credentials using service key
cred = credentials.Certificate("service_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# establish flask settings
app = Flask(__name__)
app.secret_key = "zaq12wsx"

# function to determine if a firestore query is empty
def queryIsEmpty(query):
    list = []
    for doc in query:
        list.append(doc)
    if len(list) == 0:
        return True
    else:
        return False

# function to generate the password based on a given starting digit
def generatePassword(x):
    password = ''
    for y in range(6):
        if(x > 9):
            x = 0
        password += str(x)
        x+=1
    return password

# function to update the initial data to the firestore database
def initialWrite():

    # define the base values for users
    studentID = 's3298931'
    name = 'BenObrien'

    # loop through 10 users
    for x in range(10):
        id = studentID + str(x)
        user_name = name + str(x)
        password = generatePassword(x)

        # update the database if it doesn't already exist
        docs = db.collection('default').where('id', '==', id).get()
        if queryIsEmpty(docs):
            data={'id':id, 'user_name':user_name, 'password':password}
            db.collection('default').document().set(data)

# function to validate id and password
def validate(id, pw):
    
    # check if id is contained in db
    docs = db.collection('default').get()
    found = False
    for doc in docs:
        if doc.to_dict()['id']==id:
            found = True
            correctPassword = doc.to_dict()['password']
            break
    if not found:
        return False
    # check the password
    if correctPassword == pw:
        return True
    else:
        return False

            

# home page
@app.route("/")
def home():
    
    # check for existing records in the firebase database and update if required
    initialWrite()
    
    return render_template("index.html")

# login page
@app.route("/login/", methods=["POST", "GET"])
def login():

    if request.method == "POST":
        userId = request.form["user-id"]
        pw = request.form["pw"]
        session["user-id"] = userId
        session["pw"] = pw

        # validate login details
        # if validate(user-id, pw):
        return redirect(url_for("user"))
        
    else:
        if "user-id" in session:
            return redirect(url_for("user"))

        return render_template("login.html")

# user page
@app.route("/user/")
def user():
    if "user-id" in session:
        userId = session["user-id"]
        return f"<p>User ID: {userId} is logged in</p>"
    else:
        return redirect(url_for("login"))

# user page
@app.route("/logout/")
def logout():
    session.pop("user-id", None)
    session.pop("pw", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)