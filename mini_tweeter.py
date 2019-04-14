from flask import Flask, jsonify, request, current_app
from flask.json import JSONEncoder
from sqlalchemy import create_engine, text


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
        new_user_id = insert_user(new_user)
        new_user = get_user(new_user_id)

        return jsonify(new_user)

    @app.route("/tweet", methods=['POST'])
    # tweet post endpoint. post tweet under user account
    # character limit per tweet is 300
    def tweet():
        user_tweet = request.json
        tweet = user_tweet['tweet']

        if len(tweet) > 300:
            return 'No more than 300 characters!', 400

        insert_tweet(user_tweet)

        return '', 200

    @app.route("/follow", methods=['POST'])
    # Follow endpoint
    # if user_id does not have follow field, empty field will be created automatically
    # return user information with following status
    def follow():
        payload = request.json
        insert_follow(payload)

        return '', 200

    @app.route("/unfollow", methods=['POST'])
    # Unfollow endpoint
    # return user information with following status
    def un_follow():
        payload = request.json
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


