from copyreg import constructor
from pickle import TRUE
from flask import Flask, render_template, session, request, redirect, flash , jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from dotenv import load_dotenv
from os import getenv
import random
import json

load_dotenv()

ADMIN_PASSWORD = getenv("ADMIN_PASSWORD")
ADMIN_USERNAME = getenv("ADMIN_USERNAME")
DATABASE_URI = getenv("DATABASE_URI")
DEV = getenv("DEV")
NUM_ROUNDS = int(getenv("NUM_ROUNDS"))
PORT = getenv("PORT")
SECRET_KEY = getenv("SECRET_KEY")

app = Flask(__name__)
app.debug = DEV == "True"

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.secret_key = SECRET_KEY

db = SQLAlchemy(app)

class Game(db.Model):
    __tablename__ = "game"
    game_id = db.Column(db.String(50), primary_key=True)
    round_num = db.Column(db.Integer)
    game_end = db.Column(db.Boolean, unique=False, default=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"{self.game_id}"


class Choice(db.Model):
    __tablename__ = "choice"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), nullable=False)
    game_id = db.Column(db.String(50), nullable=False)
    round_num = db.Column(db.Integer)
    number_chosen = db.Column(db.Integer, default=0)

    def __repr__(self) -> str:
        return f"{self.username} - {self.game_id}"


class UserSession(db.Model):
    __tablename__ = "usersession"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(50), nullable=False)
    game_id = db.Column(db.String(50), nullable=False)
    points = db.Column(db.Float, nullable=False, default=0.0)

db.create_all()

@app.route('/user_invalid_game_entry', methods=['GET'])
def user_invalid_game_entry():
    game_id = request.args.get('game_id')
    return jsonify(flag = (Game.query.filter_by(game_id=game_id, game_end=False).first() is None))


@app.route('/user_exists_in_game', methods=['GET'])
def user_exists_in_game():
    username , game_id = request.args.get('username') , request.args.get('game_id')
    return jsonify(flag = (UserSession.query.filter_by(username=username, game_id=game_id).first() is not None))

@app.route('/user_add_to_game', methods=['POST'])
def user_add_to_game():
    username , email ,game_id = request.json['username'] , request.json['email'] , request.json['game_id']
    new_user = UserSession(username=username, email=email, game_id=game_id, points=0.0)
    db.session.add(new_user)
    db.session.commit()
    return jsonify(sucess = True)

@app.route('/user_invalid_game_play', methods=['GET'])
def user_invalid_game_play():
    username , game_id , round_num = request.args.get('username') , request.args.get('game_id') , int(request.args.get('round_num'))
    
    cond1 = (
        Game.query.filter_by(
            game_id=game_id, round_num=round_num, game_end=False
        ).first()
        is None
    )
    cond2 = (
        UserSession.query.filter_by(username=username, game_id=game_id).first() is None
    )
    cond3 = (
        Choice.query.filter_by(
            username=username, game_id=game_id, round_num=round_num
        ).first()
        is not None
    )

    return jsonify(flag = (cond1 or cond2 or cond3))

@app.route('/user_add_choice', methods=['POST'])
def user_add_choice():
    
    username, game_id, round_num, number_chosen = request.json['username'] , request.json['game_id'] , int(request.json['round_num']) , int(request.json['number_chosen'])
    
    if (
        Choice.query.filter_by(
            username=username, game_id=game_id, round_num=round_num
        ).first()
        is not None
    ):
        return

    new_choice = Choice(
        username=username,
        game_id=game_id,
        round_num=round_num,
        number_chosen=number_chosen,
    )
    db.session.add(new_choice)
    db.session.commit()

    return jsonify(success = True)

@app.route('/user_valid_round_end', methods=['GET'])
def user_valid_round_end():
    username, game_id, round_num = request.args.get('username') , request.args.get('game_id') , int(request.args.get('round_num'))
    cond1 = (
        Game.query.filter_by(
            game_id=game_id, round_num=round_num + 1, game_end=False
        ).first()
        is not None
    )
    cond2 = (
        Choice.query.filter_by(
            username=username, game_id=game_id, round_num=round_num
        ).first()
        is not None
    )
    return jsonify(flag = (cond1 and cond2))

@app.route('/admin_start_game', methods=['POST'])
def admin_start_game():
    game_id = request.json['game_id']
    new_game = Game(game_id=game_id, round_num=1, game_end=False)
    db.session.add(new_game)
    db.session.commit()

    return jsonify(success = True)

@app.route('/admin_end_game', methods=['POST'])
def admin_end_game():
    game_id = request.json['game_id']
    try:
        game = Game.query.filter_by(game_id=game_id).first()
        game.game_end = True
        db.session.commit()
    except:
        return jsonify(success = False)

    return jsonify(success = True)



@app.route('/admin_invalid_round_end', methods=['GET'])
def admin_invalid_round_end():
    game_id, round_num = request.args.get('game_id') , int(request.args.get('round_num'))
    return jsonify(flag = (Game.query.filter_by(game_id=game_id, round_num=round_num, game_end=False).first() is None))

@app.route('/admin_end_round', methods=['POST'])
def admin_end_round():
    game_id, round_num = request.json['game_id'] , int(request.json['round_num'])
    try:
        game = Game.query.filter_by(game_id=game_id).first()

        if round_num == NUM_ROUNDS:
            game.game_end = True
            db.session.commit()
        else:
            game.round_num = round_num + 1
            db.session.commit()

    except:
        return jsonify(success = False)

    return jsonify(success = True)

@app.route('/get_result', methods=['GET'])
def get_result():
    
    game_id, round_num , reviewing = request.args.get('game_id') , int(request.args.get('round_num')) , (request.args.get('reviewing'))
    
    reviewing = (reviewing == 'True')

    freq = dict()
    
    choices = Choice.query.filter_by(game_id=game_id, round_num=round_num).all()
    for choice in choices:
        freq[choice.number_chosen] = freq.get(choice.number_chosen, 0) + 1

    if not reviewing:

        for choice in choices:

            print(choice.username , choice.number_chosen)

            username = choice.username
            number_chosen = choice.number_chosen
            f = freq[number_chosen]

            user = UserSession.query.filter_by(
                username=username, game_id=game_id
            ).first()
            user.points = user.points + ((float(number_chosen)) / (float(f)))
            db.session.commit()

    frequency = dict()

    for i in range(1, 101):
        # frequency[i] = freq.get(i, 0) + random.randint(0, 10)
        frequency[i] = freq.get(i, 0)

    userlist = UserSession.query.filter_by(game_id=game_id).all()
    ranklist = []

    for user in userlist:
        curr = user.__dict__
        ranklist.append(dict({
            'username' : curr['username'],
            'email' : curr['email'],
            'points' : curr['points']
        }))

    ranklist = sorted(ranklist, key=lambda d: d["points"], reverse=True)


    return jsonify(ranklist = ranklist, frequency = frequency)

if __name__ == "__main__":
    app.run(debug=True, port=PORT)