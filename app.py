from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import sessionmaker
from models import Base, User, Category, Blogpost, Comment
import jwt
import datetime
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://robert:moss@localhost/blog_api_db'
app.config['SECRET_KEY'] = 'thisissecret'
DATABASE_URI = 'postgresql://robert:moss@localhost/blog_api_db'
db = SQLAlchemy(app)

# read docs for this approach...
# is it a better way to structure config?
engine = create_engine(DATABASE_URI)
Base.metadata.create_all(engine)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/')
def index():
    return "<h1> welcome to this RESTfull API</h1>"

# making the decorator..
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

        if not token:
            return jsonify({"message" : "Token is missing"}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'])
            current_user = session.query(User).filter_by(id=data['user_id']).first()
            # print(current_user.name)
        except:
            return jsonify({"message" : "Token is invalid"}), 401

        return f(current_user, *args, **kwargs)
    return decorated

# This function is not necessary at this point
@app.route('/user/<user_id>', methods=['GET'])
@token_required
def get_one_user(user_id):

    user = session.query(User).get(user_id)

    if not user:
        return jsonify({"message:" : "The user does not exist" })

    user_data = {}
    user_data['id'] = user.id
    user_data['name'] = user.name
    user_data['email'] = user.email
    user_data['password'] = user.password
    user_data['admin'] = user.admin

    return jsonify({"user" : user_data})

@app.route('/user', methods=['GET'])
@token_required
def get_users(current_user):

    # returns a list of User-objects
    users = session.query(User).all()

    user_output = []

    for user in users:
        data = {}
        data['id'] = user.id
        data['name'] = user.name
        data['email'] = user.email
        data['password'] = user.password
        data['admin'] = user.admin
        user_output.append(data)

    return jsonify({"users" : data})

# Why does the trailing / need to be ther?
# This function is not necessary, since amdmin is the only active user..
@app.route('/user/', methods=['POST'])
@token_required
def create_user():
    # gets the json object anc converts it.
    # Should not be force=True

    data = request.get_json(force=True)
    hashed_password = generate_password_hash(data['password'], method='sha256')
    new_user = User(name = data['name'], email = data['email'], password = hashed_password, admin = False)
    session.add(new_user)
    session.commit()
    return jsonify({"message" : "user created"})

# Update user to admin
@app.route('/user/<user_id>', methods=['PUT'])
@token_required
def make_admin(user_id):
    user = session.query(User).get(user_id)

    if not user:
        return jsonify({"message:" : "The user does not exist" })

    user.admin = True
    session.commit()
    return jsonify({"message" : "User has been made admin"})

@app.route('/user/<user_id>', methods=['DELETE'])
@token_required
def delete_user(user_id):
    user = session.query(User).get(user_id)
    if not user:
        return jsonify({"message:" : "The user does not exist" })

    session.delete(user)
    session.commit()

    return jsonify({'message' : 'the user has been deleted!'})

@app.route('/login')
def login():
    auth = request.authorization

    if not auth or not auth.username or not auth.password:
        return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

    user = session.query(User).filter_by(name=auth.username).first()
    #print(user.name)
    if not user:
        return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

    if check_password_hash(user.password, auth.password):
        token = jwt.encode({'user_id' : user.id, 'exp' : datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'])
        return jsonify({"token" : token.decode('UTF-8')})

    return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

"""
Endpoint that concerns blogposts
"""

@app.route('/blogpost', methods=['POST'])
def create_blogpost():

    data = request.get_json(force=True)
    new_blogpost = Blogpost(name = data['name'], content = data['content'], author_id = data['author_id'])
    session.add(new_blogpost)
    session.commit()
    return jsonify({"message" : "post created"})

@app.route('/blogpost', methods=['GET'])
def get_all():

    blogposts = session.query(Blogpost).all()

    blogpost_output = []

    for post in blogposts:
        data = {}
        data['id'] = post.id
        data['name'] = post.name
        data['content'] = post.content
        data['author_id'] = post.author_id
        data['created_at'] = post.created_at
        data['modified_at'] = post.modified_at
        blogpost_output.append(data)

    return jsonify({"blogposts" : blogpost_output})

# how to implement that only one or the other Columne get updatet
# Does one need sevral routes?
@app.route('/blogpost/<blogpost_id>', methods=['PUT'])
def update_blogpost(blogpost_id):
    blogpost = session.query(Blogpost).get(blogpost_id)
    print(blogpost)
    name = request.get_json(['name'])
    content = request.get_json(['content'])

    blogpost.content = content['content']
    blogpost.name = name['name']

    blogpost.modified_at = datetime.datetime.utcnow()
    session.add(blogpost)
    session.commit()
    return jsonify({"message" : "Blogpost has been updated..."})

@app.route('/blogpost/<blogpost_id>', methods=['DELETE'])
def delete_blogpost(blogpost_id):
    blogpost = session.query(Blogpost).get(blogpost_id)
    if not blogpost:
        return jsonify({"message:" : "The user does not exist"})

    session.delete(blogpost)
    session.commit()
    return jsonify({"message" : "The blogpost is deleted..."})

"""
Endpoints that conserns comments
"""

@app.route('/comment', methods=['POST'])
def create_comment():
    data = request.get_json(force=True)
    new_comment = Comment(email = data['email'], content = data['content'], blogpost_id = data['blogpost_id'])
    session.add(new_comment)
    session.commit()
    return jsonify({"message" : "comment created"})

@app.route('/comment', methods=['GET'])
def get_comments():
    comments = session.query(Comment).all()

    comment_output = []

    for comment in comments:
        data = {}
        data['id'] = comment.id
        data['email'] = comment.email
        data['content'] = comment.content
        data['blogpost_id'] = comment.blogpost_id
        data['created_at'] = comment.created_at
        comment_output.append(data)

    return jsonify({"Comments" : comment_output})

"""
Endpoints that concerns categorys
"""

@app.route('/category', methods=['POST'])
def create_category():
    blogpost = session.query(Blogpost).get(1)
    data = request.get_json(force=True)
    new_category = Category(name = data['name'], blogpost = blogpost)
    session.add(new_category)
    session.commit()

    return jsonify({"message" : "category is created..."})

@app.route('/category', methods=['GET'])
def get_categorys():
    categorys = session.query(Category).all()

    category_output = []

    for category in categorys:
        data = {}
        data['id'] = category.id
        data['name'] = category.name
        data['blogpost_id'] = category.blogpost_id
        category_output.append(data)

    return jsonify({"Categorys" : category_output})


"""
Test route..
"""
@app.route('/test_relation', methods=['GET'])
def test():
    author = session.query(Blogpost).filter_by(author_id=2).first()
    category = session.query(Category).filter_by(name='testpost').first()
    return jsonify({"message" : "testing..."})
