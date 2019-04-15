from flask import Flask, jsonify, request, current_app, Response, g
from flask.json import JSONEncoder
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from functools import wraps
import bcrypt
import jwt


class CustomJSONEncoder(JSONEncoder):
    # Default JSON encoder can't convert set to list, so this class convert set to list
    # so we can convert set data to JSON format
    def default(self, o):
        if isinstance(o, set):
            return list(o)

        return JSONEncoder.default(self, o)


def get_user(user_id):
    # Find user from DB
    # Input: user_id
    # Return: User information in JSON format
    user = current_app.database.execute(text("""
        SELECT
            id,
            name,
            email,
            profile
        FROM users
        WHERE id = :user_id
    """), {
        'user_id' : user_id
    }).fetchone()

    return {
        'id' : user['id'],
        'name' : user['name'],
        'email' : user['email'],
        'profile' : user['profile']
    } if user else None


def insert_user(user):
    # Register new user in DB
    # Input: user info
    return current_app.database.execute(text("""
        INSERT INTO users (
            name,
            email,
            profile,
            hashed_password
        ) VALUES (
            :name,
            :email,
            :profile,
            :password
        )
    """), user).lastrowid


def insert_tweet(user_tweet):
    # Post User tweet in DB
    # Input: user's tweet
    return current_app.database.execute(text("""
        INSERT INTO tweets (
            user_id,
            tweet
        ) VALUES (
            :id,
            :tweet
        )
    """), user_tweet).rowcount


def insert_follow(user_follow):
    # Register follower to user follower list in DB
    # Input: Follow ID
    return current_app.database.execute(text("""
        INSERT INTO users_follow_list (
            user_id,
            follow_user_id
        ) VALUES (
            :id,
            :follow
        )
    """), user_follow).rowcount


def insert_unfollow(user_unfollow):
    # Remove unfollow user ID from user follow list in DB
    # Input: Unfollow user ID
    return current_app.database.execute(text("""
        DELETE FROM users_follow_list
        WHERE user_id = :id
        AND follow_user_id = :unfollow
    """), user_unfollow).rowcount


def get_timeline(user_id):
    # Show all follower's tweets
    # Input: User ID
    timeline = current_app.database.execute(text("""
        SELECT 
            t.user_id,
            t.tweet
        FROM tweets t
        LEFT JOIN user_follow_list ufl ON ufl.user_id = :user_id
        WHERE t.user_id = :user_id
        OR t.user_id = ufl.follow_user_id
    """), {
        'user_id' : user_id
    }).fetchall()

    return [{
        'user_id' : tweet['user_id'],
        'tweet' : tweet['tweet']
    } for tweet in timeline]


def get_uset_id_and_password(email):
    row = current_app.database.execute(text("""
        SELECT
            id,
            hashed_password
        FROM users
        WHERE email = :email
    """), {'email' : email}).fetchone()

    return {
        'id' : row['id'],
        'hashed_password' : row['hashed_password']
    } if row else None


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        access_token = request.headers.get('Authorization')
        if access_token is not None:
            try:
                payload = jwt.decode(access_token, current_app.config['JWT_SECRET_KEY'], 'HS256')
            except jwt.InvalidTokenError:
                payload = None

            if payload is None: return Response(status=401)

            user_id = payload['user_id']
            g.user_id = user_id
            g.user = get_user(user_id) if user_id else None
        else:
            return Response(status=401)

        return f(*args, **kwargs)

    return decorated_function


def create_app(test_config=None):
    # Creating Endpoint for Front end
    # Setup DB information through config.py or parameter which is test_config
    # Config for DB connection
    app = Flask(__name__)

    # assign Custom JSON encoder as default in this program
    app.json_encoder = CustomJSONEncoder

    if test_config is None:
        app.config.from_pyfile("config.py")
    else:
        app.config.update(test_config)

    database = create_engine(app.config['DB_URL'], encoding = 'utf-8', max_overflow = 0)
    app.database = database

    @app.route("/Pingapi", methods=['GET'])
    # Verification endpoint whether server is alive or not
    # If server works, it'll return 'pong'
    def ping():
        return 'pong'

    @app.route("/signup", methods=['POST'])
    # sign up endpoint. Register user, then return user information with user_ID
    def sign_up():
        new_user = request.json
        new_user['password'] = bcrypt.hashpw(
            new_user['password'].encode('UTF-8'),
            bcrypt.gensalt()
        )
        new_user_id = insert_user(new_user)
        new_user = get_user(new_user_id)

        return jsonify(new_user)

    @app.route('/login', methods=['POST'])
    # login endpoint
    # Authentication is applied
    # Return Access Token, and it'll be used to follow, unfollow and tweet endpoint
    def login():
        credential = request.json
        email = credential['email']
        password = credential['password']
        user_credential = get_uset_id_and_password(email)

        if user_credential and bcrypt.checkpw(password.encode('UTF-8'), user_credential['hashed_password'].encode('UTF-8')):
            user_id = user_credential['id']
            payload = {
                'user_id' : user_id,
                'exp' : datetime.utcnow() + timedelta(seconds = 60 * 60 * 24)
            }
            token = jwt.encode(payload, app.config['JWT_SECRET_KEY'], 'HS256')

            return jsonify({
                'access_token' : token.decode('UTF-8')
            })
        else:
            return '', 401

    @app.route("/tweet", methods=['POST'])
    @login_required
    # tweet post endpoint. post tweet under user account
    # character limit per tweet is 300
    # Call: localhost:5000/tweet tweet='Message' 'Authorization:access_token'
    def tweet():
        user_tweet = request.json
        user_tweet['id'] = g.user_id
        tweet = user_tweet['tweet']

        if len(tweet) > 300:
            return 'No more than 300 characters!', 400

        insert_tweet(user_tweet)

        return '', 200

    @app.route("/follow", methods=['POST'])
    @login_required
    # Follow endpoint
    # if user_id does not have follow field, empty field will be created automatically
    # return user information with following status
    # Call: localhost:5000/follow follow=following_id 'Authorization:access_token'
    def follow():
        payload = request.json
        payload['id'] = g.user_id
        insert_follow(payload)

        return '', 200

    @app.route("/unfollow", methods=['POST'])
    @login_required
    # Unfollow endpoint
    # return user information with following status
    # Call: localhost:5000/unfollow follow=following_id 'Authorization:access_token'
    def un_follow():
        payload = request.json
        payload['id'] = g.user_id
        insert_unfollow(payload)

        return '', 200

    @app.route("/time_line/<int:user_id>", methods=['GET'])
    # timeline endpoint.
    # return follower's post
    def timeline(user_id):
        return jsonify({
            'user_id': user_id,
            'timeline': get_timeline(user_id)
        })

    return app


