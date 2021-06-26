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
        session.permanent = True
        user = request.form["nm"]
        age = request.form["age"]
        city = request.form["city"]
        session["user"] = user
        session["age"] = age
        session["city"] = city
        return redirect(url_for("user"))
    else:
        if "user" in session:
            return redirect(url_for("user"))

        return render_template("login.html")

# user page
@app.route("/user/")
def user():
    if "user" in session:
        user = session["user"]
        age = session["age"]
        city = session["city"]
        return f"<p>User name: {user}</p><p>User age: {age}</p><p>User city: {city}</p>"
    else:
        return redirect(url_for("login"))

# user page
@app.route("/logout/")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)