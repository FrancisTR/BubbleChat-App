from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase

#Import Date
from datetime import datetime

#Import File related
from werkzeug.utils import secure_filename
from PIL import Image
import base64
import io
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session

#.env
from dotenv import load_dotenv
import os

#Setting up the web application
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv('Flask_Key')
socketio = SocketIO(app)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SESSION_TYPE'] = 'sqlalchemy'

#Database
db = SQLAlchemy(app)
app.config['SESSION_SQLALCHEMY'] = db
Session(app)





#Initialize variables
rooms = {} #List of rooms created
username = [] #Store Usernames that exists so far




@app.route("/", methods=["POST", "GET"]) #POST and GET request for home
def home():
    #session.clear() #Be able to navigate through different rooms
    if request.method == "POST":
        #Grabbing values in the form
        name = request.form.get("name")
        code = request.form.get("code")
        #Buttons to either Join or Create the Room
        #False is the default if it does not exist since one of them is going to be pressed
        join = request.form.get("join", False)
        create = request.form.get("create", False)
        #Either choosing the Profile Icons built in or uploading your Custom Icon
        ProfileIcon = request.form.get("ProfileIcon", False)
        CustomIcon = request.files['ProfileIcon']

        if ((ProfileIcon == False or ProfileIcon == "") and CustomIcon.filename == ""): #Default Icon if no icons are chosen from either options
            ProfileIcon = '/static/css/Default.png'
        elif (ProfileIcon == "Icon1"):
            ProfileIcon = '/static/css/Icon1.png'
        elif (ProfileIcon == "Icon2"):
            ProfileIcon = '/static/css/Icon2.jpg'
        elif (ProfileIcon == "Icon3"):
            ProfileIcon = '/static/css/Icon3.gif'
        elif (ProfileIcon == "Icon4"):
            ProfileIcon = '/static/css/Icon4.gif'
        else: #Custom Icon

            filename = secure_filename(CustomIcon.filename)
            img = Image.open(CustomIcon.stream)

            data = io.BytesIO()
            if (".png" in CustomIcon.filename):
                img.save(data, "png")
                encode_img_data = base64.b64encode(data.getvalue())
                ProfileIcon = "data:image/png;base64,"+encode_img_data.decode("UTF-8")
            elif (".jpeg" in CustomIcon.filename):
                img.save(data, "jpeg")
                encode_img_data = base64.b64encode(data.getvalue())
                ProfileIcon = "data:image/jpg;base64,"+encode_img_data.decode("UTF-8")
            elif(".gif" in CustomIcon.filename):
                img.save(data, "gif")
                encode_img_data = base64.b64encode(data.getvalue())
                ProfileIcon = "data:image/gif;base64,"+encode_img_data.decode("UTF-8")
        print(f"This is my Profile Icon: {ProfileIcon}")



        #----User Conditions----

        #Conditions need to be met before entering/creating a room
        #Display the error on the client side
        if not name: #No name inputted
            return render_template("home.html", error="Please Enter a Name.", code=code, name=name)
        if join != False and not code: #No code inputed IF the user click on the Join Button
            return render_template("home.html", error="Please Enter a Room Code.", code=code, name=name)

        #If created a room, give a unique code
        room = code
        #Additional conditions
        if create != False: #If creating a room, create a unique code with only one member to start off with (counting as the user)
            room = generate_unique_code(4)
            rooms[room] = {"members": 1, "messages": []}
        elif code not in rooms: #If the code inputted does not exist in the list of rooms, display error
            return render_template("home.html", error="Room does not Exist.", code=code, name=name)
        elif name in username: #If there is already an existing username on the server-side, display error
            return render_template("home.html", error="Username already Exist.", code=code, name=name)

        #----------------------


        #Store information to the user in a session (Temporary data in the server)
        session["room"] = room #room code
        session["name"] = name #Username
        session["ProfileIcon"] = ProfileIcon #Store the profile picture in a session
        
        return redirect(url_for("room")) #Go to room.html

    return render_template("home.html") #Show the home.html as default






#Generate a unique code for the user to join
def generate_unique_code(length):
    while(True):
        code = ""
        for _ in range(length): #Generate a certain length of random ascii letters
            code += random.choice(ascii_uppercase)

        #If the code is unique and does not currently exist, break out of the loop. Otherwise, randomized again
        if code not in rooms:
            break
    
    return code






@app.route("/room")
def room(): #room.html
    room = session.get("room")
    Icon = session.get("ProfileIcon")
    #If any options is true that the room does not exist, name does not exist, and the room is not in the rooms list, then go back to the main page (home.html)
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))
    #Otherwise, render the room.html with the code, messages, number of members, and user's icon on the client-side
    return render_template("room.html", code=room, messages=rooms[room]["messages"], members=rooms[room]["members"], icon=Icon)






@socketio.on("message")
def message(data): #Messages itself for the client-side
    room = session.get("room")
    #If room does not exist, simply stop this function
    if room not in rooms:
        return
    
    ProfileIcon = session.get("ProfileIcon")

    #Format our date of the message sent
    currentDate = datetime.now() #Current date. Time is 0-24
    HourTime = int(currentDate.strftime("%H")) #Get the Hour
    if (HourTime <= 11): # Morning (AM) from 0-11AM
        if (HourTime == 0):
            HourTime = 12
        AMPM = "AM"
    elif (HourTime >= 12): #PM from 12(noon)-11PM
        if (HourTime != 12):
            HourTime = HourTime - 12
        AMPM = "PM"
    messageDate = currentDate.strftime(str(HourTime)+":%M "+AMPM) #Format the time into a string


    #Store values in the 'content' dictionary and send it to the room.html
    content = {
        "name": session.get("name"),
        "message": data["data"],
        "ProfileIcon": ProfileIcon,
        "messageDate": messageDate
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}") #Display in IDE console for Testing






@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    #Stop if there is no room or no name
    if not room or not name:
        return
    if room not in rooms: #have a room but not valid
        leave_room(room)
        return
    #Otherwise, join the room
    join_room(room) #put the user in a room

    #Let everyone know that a user join the room
    send({"name": "", "message": "<Font color='orange'><i>'"+name+"'</i> has entered the room</Font>"}, to=room) #Send this message to everyone
    rooms[room]["members"] += 1 #How many people are in the room. Add 1 since they joined

    #Added the username in the list
    username.append(name)
    print(f"{name} joined room {room}") #Print in IDE console for Testing
    return render_template("room.html", members=rooms[room]["members"]) #Render the updated version to room.html






@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    #If the rooms are in rooms when they diconnect
    if room in rooms:
        rooms[room]["members"] -= 1 #remove 1 member from the list
        #Delete the username
        username.remove(name)
        if rooms[room]["members"] <= 1: #if room empty, delete it
            del rooms[room]
    send({"name": "", "message": "<Font color='#FF6600'><i>'"+name+"'</i> has left the room</Font>"}, to=room) #Send this message to everyone
    print(f"{name} has left the room {room}") #Print on the IDE console for Testing
    return render_template("room.html", members=rooms[room]["members"]) #Update room.html





#Run the app on socketIO
if __name__ == "__main__":
    socketio.run(app, debug=True) #Prevents from us rerunning the server
    #app.run(host="0.0.0.0", port=5000)
    
    #with app.app_context():
    #    db.create_all()