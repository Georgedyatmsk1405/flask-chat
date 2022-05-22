import flask
import json

from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_login import login_user, LoginManager, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from wtforms import StringField, PasswordField,SubmitField, IntegerField, Form
from flask_wtf import FlaskForm
from flask_socketio import SocketIO, send
from sqlalchemy import func
import base64
import os
app= Flask(__name__)
UPLOAD_FOLDER = 'static\path'
app.secret_key = "super secret key"
app.config["SESSION_PERMANENT"] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY']='thisissecretkey'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)
socketio = SocketIO(app)
socketid=[]
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
login_manager=LoginManager()
login_manager.init_app(app)
login_manager.login_view="login"
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class ChatMessages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(256))
    msg = db.Column(db.Text)
    chat = db.Column(db.Integer)
    data=db.Column(db.Integer)
    filename=db.Column(db.String(256), default='no')


class Chat(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    chat_id = db.Column(db.Integer)
    User_id= db.Column(db.Integer)



friends = db.Table('friends',
db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
db.Column('friend_id', db.Integer, db.ForeignKey('user.id'))
)


users={}

class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    email = db.Column(db.String)
    password = db.Column(db.String)
    authenticated = db.Column(db.Boolean, default=False)

    friends = db.relationship('User',  # defining the relationship, User is left side entity
                              secondary=friends,
                              primaryjoin=(friends.c.user_id == id),
                              secondaryjoin=(friends.c.friend_id == id),
                              lazy='dynamic'
                              )

    def __init__(self, email, password):
        self.email = email
        self.password = password

    def is_active(self):
        """True, as all users are active."""
        return True

    def get_id(self):
        """Return the email address to satisfy Flask-Login's requirements."""
        return self.id

    def is_authenticated(self):
        """Return True if the user is authenticated."""
        return self.authenticated

    def is_anonymous(self):
        """False, as anonymous users aren't supported."""
        return False





@login_manager.user_loader
def user_loader(user_id):
    return User.query.get(user_id)

@app.route("/add_friend", methods=["GET", "POST"])
def add_friend():
    error=''
    user=current_user
    friendslist=user.friends
    print(friendslist)

    if request.method == "POST":
        email = str(request.form.get('name'))
        friend = User.query.filter_by(email=email).first()
        result = db.engine.execute('select * from friends where friends.user_id=:a and friends.friend_id=:b',{'a':user.id,'b':friend.id})
        chekfriend=[row[0] for row in result]
        print(chekfriend)
        if len(chekfriend) == 0:

            statement = friends.insert().values(user_id=current_user.id, friend_id=friend.id)
            statement2= friends.insert().values(user_id=friend.id, friend_id=current_user.id)
            db.session.execute(statement)
            db.session.execute(statement2)
            db.session.commit()
        else:
            error='вы уже добавили его в друзья'
    return render_template('friends.html', friendslist=friendslist, error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    error=''
    if request.method == "POST":
        email = str(request.form.get('uname'))
        password = str(request.form.get('psw'))

        user = User.query.filter_by(email=email).first()
        print(user)
        if user:
            return render_template('register.html', error='user already exist')
        else:
            new_user=User(email,password)
            db.session.add(new_user)
            db.session.commit()
        return redirect(url_for("createchat"))
    return render_template('register.html')

@app.route("/login", methods=["GET", "POST"])
def login():


    """For GET requests, display the login form.
    For POSTS, login the current user by processing the form.

    """


    if request.method=="POST":
        email=str(request.form.get('uname'))
        password=str(request.form.get('psw'))

        user = User.query.filter_by(email=email).one()
        print(user)
        if user:
            if user.password==password:
                user.authenticated = True
                print("мы тут")
                db.session.add(user)
                db.session.commit()
                login_user(user, remember=True)
                return redirect(url_for("createchat"))
    return render_template("login.html")


@app.route("/filehandler", methods=["GET", "POST"])
def filehandler():
    print('sdsds')
    if request.method == 'POST':
        print('sdsds')
        print(request.form.get('chat'))

        messmax = ChatMessages.query.with_entities(ChatMessages.data).all()
        print('messsmax'+str(messmax))
        if len(messmax) == 0:
            max_logins = 0
            max_logins += 1
        else:
            max_logins = max(messmax)
            max_logins = max_logins[0] + 1
        print('succse')

        data=int(request.form.get('chat'))
        userr = current_user.email
        file = request.files['file']
        #print(file.filename)
        #msg = base64.b64encode(file.read())
        #print(file.read())
        filename=str(max_logins)+'.'+str(file.filename.split('.')[-1])

        print(filename)


        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        message = ChatMessages(username=userr, msg='файл', chat=data,data=max_logins, filename=filename)
        db.session.add(message)

        db.session.commit()

        print('did it')

        
        return redirect(url_for('main',chat_id=data))



@app.route("/createchat", methods=["GET", "POST"])
def createchat():
    #print(current_user.email)
    chatnumber=Chat.query.filter_by(User_id=current_user.id).all()
    print(chatnumber)

    if request.method == 'POST' and 'name':
        name=str(request.form.get('name'))
        friend=User.query.filter_by(email=name).first()
        chatmax = Chat.query.with_entities(Chat.chat_id).all()
        print(chatmax)
        if len(chatmax) == 0:
            max_logins = 0
            max_logins += 1
        else:
            max_logins = max(chatmax)
            max_logins = max_logins[0] + 1
        print(max_logins)

        print(friend.id)
        chat = Chat(User_id=current_user.id, chat_id=max_logins)
        chatfriend = Chat(User_id=friend.id, chat_id=max_logins)
        db.session.add(chat)
        db.session.add(chatfriend)
        db.session.commit()

        #chatnumber=Chat.query.filter_by(User_id=current_user.id)



    return render_template('createchat.html',chatnumber=chatnumber)

@app.route("/delete/<int:chat_id>", methods=["GET", "POST"])
def delete(chat_id):
    message=ChatMessages.query.get(chat_id)
    db.session.delete(message)
    db.session.commit()
    return 'ok'

@app.route("/main/<int:chat_id>", methods=["GET", "POST"])
def main(chat_id):
    chat=Chat.query.filter_by(chat_id=chat_id).with_entities(Chat.User_id).all()
    list=[x[0] for x in chat]
    listt = []
    for i in list:
        chatt=User.query.filter_by(id=i).with_entities(User.email).all()
        listt.append(chatt[0][0])




    print(list)


    if current_user.id not in list:
        return 'нет доступа'
    else:

        user = current_user.email


        messages=ChatMessages.query.filter_by(chat=chat_id)

        imageslist=[]




    print(user)

    return render_template('main.html',chat_id=chat_id, messages=messages, user=user, friends=listt)
@socketio.on('message')
def handleMessage(data):
    global users

    print('реквест айди отправителя'+str(request.sid))



    print(data)
    if current_user.is_authenticated:
        user=str(data['user']).strip()
        print(user)
        userr=User.query.filter_by(email=user).one()
        print(userr)
        chat=int(data['chat'])
        chat_list = Chat.query.with_entities(Chat.User_id).filter_by(chat_id=chat).all()
        chat_list=[x[0] for x in chat_list]
        print(chat_list)
        print(data['friends'])
        friendd=data['friends'].replace(']','').replace('[','').replace("'","").replace('\n','').split(',')
        friendd=[x.strip() for x in friendd]
        print(friendd)
        print(users)



        if userr.id not in chat_list:
            pass
        else:
            for i in friendd:
                print(i)

                if i in users[chat]:
                    print(users[chat][i])
                    sisid=users[chat][i]
                    print(sisid)
                    send(data,to=sisid)
            messmax = ChatMessages.query.with_entities(ChatMessages.data).all()
            print( messmax)
            if len( messmax) == 0:
                max_logins = 0
                max_logins += 1
            else:
                max_logins = max(messmax)
                max_logins = max_logins[0] + 1

            #databinary = base64.b64decode(data['base64String'])

            message = ChatMessages(username=current_user.email, msg=data['msg'], chat=data['chat'],data=max_logins)
            db.session.add(message)

            db.session.commit()


@socketio.on('username', namespace='/private')
def recieve_username(privatem):
    print('получиличчч'+str(privatem))
    user=current_user.email
    print(user)
    chat=int(privatem['chat'])
    print(chat)

    if chat not in users:
        users[chat]={user:privatem['sisid']}
    else:
        new_pairs=[ (user,privatem['sisid'])]
        users[chat].update(new_pairs)





    print(users)

    print('получили айд '+str(privatem))



if __name__ == '__main__':
    app.run(debug=True)
    socketio.run(app)
