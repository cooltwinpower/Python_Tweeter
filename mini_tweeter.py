from flask import Flask, jsonify, request
from flask.json import JSONEncoder


class CustomJSONEncoder(JSONEncoder):
    # Default JSON encoder can't convert set to list, so this class convert set to list
    # so we can convert set data to JSON format
    def default(self, o):
        if isinstance(o, set):
            return list(o)

        return JSONEncoder.default(self, o)


app = Flask(__name__)
app.users = {}
app.id_count = 1
app.tweets = []

# assign Custom JSON encoder as default in this program
app.json_encoder = CustomJSONEncoder


@app.route("/Pingapi", methods=['GET'])
# Verification endpoint whether server is alive or not
# If server works, it'll return 'pong'
def ping():
    return 'pong'


@app.route("/signup", methods=['POST'])
# sign up endpoint. Register user, then return user information with user_ID
def sign_up():
    new_user = request.json
    new_user["id"] = app.id_count
    app.users[app.id_count] = new_user
    app.id_count = app.id_count + 1

    return jsonify(new_user)


@app.route("/tweet", methods=['POST'])
# tweet post endpoint. post tweet under user account
# character limit per tweet is 300
def tweet():
    payload = request.json
    user_id = int(payload['id'])
    tweet = payload["tweet"]

    if user_id not in app.users:
        return 'Invalis user id', 400

    if len(tweet) > 300:
        return 'No more than 300 characters!', 400

    user_id = int(payload['id'])

    app.tweets.append({
        'user_id' : user_id,
        'tweet' : tweet
    })

    return '', 200


@app.route("/follow", methods=['POST'])
# Follow endpoint
# if user_id does not have follow field, empty field will be created automatically
# return user information with following status
def follow():
    payload = request.json
    user_id = int(payload['id'])
    follow = int(payload['follow'])

    if user_id not in app.users:
        return 'Invalid User ID', 400

    if follow not in app.users:
        return 'Invalid follower ID', 400

    user = app.users[user_id]
    user.setdefault('follow', set()).add(follow)

    return jsonify(user)


@app.route("/unfollow", methods=['POST'])
# Unfollow endpoint
# return user information with following status
def un_follow():
    payload = request.json
    user_id = int(payload['id'])
    un_follow = int(payload['un_follow'])

    if user_id not in app.users:
        return 'Invalid User ID', 400

    if un_follow not in app.users:
        return 'Invalid follower ID', 400

    user = app.users[user_id]
    user.setdefault('follow', set()).discard(un_follow)

    return jsonify(user)


@app.route("/time_line/<int:user_id>", methods=['GET'])
# timeline endpoint.
# return follower's post
def timeline(user_id):
    if user_id not in app.users:
        return 'Invalid User id', 400

    follow_list = app.users[user_id].get('follow', set())
    follow_list.add(user_id)
    timeline = [tweet for tweet in app.tweets if tweet['user_id'] in follow_list]

    return jsonify({
        'user_id' : user_id,
        'timeline' : timeline
    })