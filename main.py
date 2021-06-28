# -------------------------------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------------------------------

# imports 
from flask import Flask, redirect, url_for, render_template, request, session
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import os
from google.cloud import storage
from datetime import datetime

# setup firestore credentials using service key
cred = credentials.Certificate("service_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# google cloud storage settings
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "service_key.json"
storage_client = storage.Client()

# establish flask settings
app = Flask(__name__)
app.secret_key = "zaq12wsx"

# -------------------------------------------------------------------------------------------
# FUNCTIONS
# -------------------------------------------------------------------------------------------

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
        image_name = str(x) + ".png"

        # update the database if it doesn't already exist
        docs = db.collection('default').where('id', '==', id).get()
        if queryIsEmpty(docs):
            data={'id':id, 'user_name':user_name, 'password':password, 'image_name':image_name}
            db.collection('default').document().set(data)

# function which takes id and returns username
def getUsername(id):
    docs = db.collection('default').get()
    for doc in docs:
        if doc.to_dict()['id']==id:
            return doc.to_dict()['user_name']
            break

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

# function to change password
def changePassword(id, new_pw):

    docs = db.collection('default').get()
    for doc in docs:
        if doc.to_dict()['id']==id:
            key = doc.id
            db.collection('default').document(key).update({"password":new_pw})

# function to determine if id exists
def idExists(id):
    found = False
    docs = db.collection('default').get()
    for doc in docs:
        if doc.to_dict()['id']==id:
            found = True
            break
    return found

# function to determine if username exists
def usernameExists(username):
    found = False
    docs = db.collection('default').get()
    for doc in docs:
        if doc.to_dict()['user_name'] == username:
            found = True
            break
    return found     

# function to create a new user in the firestore db
def newUser(id, username, pw, image_name):
    data = {'id':id, 'user_name':username, 'password':pw, 'image_name':image_name}
    db.collection('default').add(data)       

# function to upload a file to Google Cloud Storage
def uploadToCloud(file, type):
    if type == 'message':
        bucket_name = 's3298931_post_images'
    else:
        bucket_name = 's3298931-a1-numbers'
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(file.filename)
    blob.upload_from_file(file)

    image_name = file.filename
    image_url = 'https://storage.cloud.google.com/' + bucket_name + '/' + image_name

    return image_url

# function to return a users image
def getImage(id):
    docs = db.collection('default').get()
    for doc in docs:
        if doc.to_dict()['id']==id:
            image_name = doc.to_dict()['image_name']
    bucket_name = 's3298931-a1-numbers'
    image_path = 'https://storage.cloud.google.com/' + bucket_name + '/' + image_name
    return image_path

# function to store a post on firestore db and upload image to google cloud storage
def uploadMessage(subject, text, image, user_id):

    # obtain the image name
    image_name = image.filename.strip()
    if not image_name:
        image_name = None
    else:
        image_name = image.filename
    
    # obtain the image url for the user
    user_image_url = getImage(user_id) 

    # update image to google cloud storage
    if image_name != None:
        image_url = uploadToCloud(image, 'message')
    else:
        image_url = None

    # update message contents to firestore db
    time = datetime.now()
    user_name = getUsername(user_id)
    data = {"subject":subject, "text":text, "image_url":image_url, "date_time":time, "user_name":user_name, "user_image_url":user_image_url}
    db.collection('messages').document().set(data)

# -------------------------------------------------------------------------------------------
# FLASK FUNCTIONALITY 
# -------------------------------------------------------------------------------------------

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
        if validate(userId, pw):
            session["logged-in-user"] = userId
            session["user-name"]=getUsername(userId)
            session["image"] = getImage(userId)
            session.pop("user-id", None)
            session.pop("pw", None)
            return redirect(url_for("forum"))
        # if username or password is invalid set the sesssion variable validated to fail
        else:
            session["val-status"] = "fail"
            session.pop("user-id", None)
            session.pop("pw", None)
            return render_template("login.html")
            
        
    else:
        if "logged-in-user" in session:
            return redirect(url_for("forum"))

        if "new_reg" in request.args:
            new_reg = request.args["new_reg"]
        elif "pw_change" in request.args:
            new_reg = "pw-change"
        else:
            new_reg = False

        return render_template("login.html", reg_status=new_reg)

# forum page
@app.route("/forum/", methods=["POST", "GET"])
def forum():
    
    # message posted
    if request.method == "POST":
        # capture message data from form
        subject = request.form["msg-subject"]
        text = request.form["msg-text"]
        if "msg-image" in request.files:
            image = request.files["msg-image"]
        else:
            image = None

        # upload message to firestore db
        uploadMessage(subject, text, image, session["logged-in-user"])

    if "logged-in-user" in session:
         # get the ten latest posts to pass to forum page
        docs = db.collection(u'messages')
        query = docs.order_by(u"date_time", direction=firestore.Query.DESCENDING).limit(10)
        results = query.get()
        return render_template("forum.html", message_data=results)
    else:
        return redirect(url_for("login"))

# user page
@app.route("/user/", methods=["POST", "GET"])
def user():
    
    # form submission
    if request.method == 'POST':
        # password edit 
        if "pw-edit" in request.form:
            id = session['logged-in-user']
            pw = request.form['old-pw']
            if validate(id, pw):
                changePassword(id, request.form['new-pw'])
                # log out user so they are prompted to log in with new password
                session.pop("logged-in-user", None)
                return redirect(url_for("login", pw_change=True))
            else:
                return redirect(url_for("user", pw_success=False))


        # post edit
        if "post-edit" in request.form:
            print("post-edit success!")
    
    if "logged-in-user" in session:
        if "pw_success" in request.args:
            return render_template("user.html", pw_success=request.args['pw_success'])
        else:
            return render_template("user.html")
    else:
        return redirect(url_for("login"))

# register page
@app.route("/register/", methods=["POST", "GET"])
def register():
    
    # pop any session values which may be present from previous attepmts
    session.pop("reg-id-status", None)
    session.pop("reg-username-status", None)
    session.pop("reg-password-status", None)
    
    # logic upon form completion
    # update variables from form
    if request.method == "POST":
        regID = request.form["reg-ID"]
        regUsername = request.form["reg-username"]
        regPw = request.form["reg-pw"]


        # check if id or username is blank or already exists in firestore db
        failure = False

        if len(regID) == 0:
            session["reg-id-status"] = "blank"
            failure = True
        elif idExists(regID):
            session["reg-id-status"] = "found"
            failure = True
        if len(regUsername) == 0:
            session["reg-username-status"] = "blank"
            failure = True
        elif usernameExists(regUsername):
            session["reg-username-status"] = "found"
            failure = True

        # check that password is not blank
        if len(regPw) == 0:
            session["reg-password-status"] = "blank"
            failure = True
        
        # check if form validation successful
        # return to register page if validation failed, proceed to login page if successful
        if(failure):
            session.pop("regId", None)
            session.pop("regUsername", None)
            session.pop("regPw", None)
            render_template("register.html")
        else:
            image = request.files["reg-Image"]
            uploadToCloud(image, 'user')
            newUser(regID, regUsername, regPw, image.filename)
            session.pop("regId", None)
            session.pop("regUsername", None)
            session.pop("regPw", None)
            return redirect(url_for("login", new_reg=True))

    return render_template("register.html")

# logout page
@app.route("/logout/")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)