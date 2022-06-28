from functools import wraps
from flask import Flask, jsonify, request, make_response
from flask_restful import Resource, Api
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from func import slugify, data_parser
import jwt
import os
import datetime

# Setup App
app = Flask(__name__)
api = Api(app)

# Setup CORS
ALOWED_HOSTS = os.environ.get('ALOWED_HOSTS', '*').split(',')
CORS(app, resources={r"/api/*": {"origins": ALOWED_HOSTS}})


# Setup DB
db = SQLAlchemy(app)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get('DATABASE_URL', None)
if DATABASE_URL is None:
    DATABASE_URL = "sqlite:///" + os.path.join(BASE_DIR, "db.sqlite")
else:
    DATA_URL = DATABASE_URL.split(':')
    DATABASE_URL = 'postgresql:' + ':'.join(DATA_URL[1:])
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '*4yv_l=hz)fy#vtovmil_xsypkbvk8qq$h_aa%)c87w@dqn=l=')

# Create Model User
class User(db.Model):
    global user_field
    user_field = ['id', 'name', 'status']

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    name = db.Column(db.String(255))
    status = db.Column(db.String(255))
    slug = db.Column(db.String(255))
    todos = db.relationship('Todos', backref='usertodo')

    # Method for save
    def save(self):
        try:
            self.slug = self.slug if self.slug is not None else slugify(self.name)
            db.session.add(self)
            db.session.commit()
            return True
        except:
            return False

    # Property for display after save
    @property
    def serialize(self):
        result = { field: getattr(self, field) for field in user_field}
        return result

class Todos(db.Model):
    global todo_field
    todo_field = ['id', 'activity', 'date', 'important', 'completed']

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    activity = db.Column(db.Text)
    date = db.Column(db.Date)
    important = db.Column(db.Boolean)
    completed = db.Column(db.Boolean)
    usertodo_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    # Method for save
    def save(self):
        try:
            date = self.date.split('-')
            self.date = datetime.date(int(date[0]), int(date[1]), int(date[2]))
            db.session.add(self)
            db.session.commit()
            return True
        except:
            return False

    
    # Property for display after save
    @property
    def serialize(self):
        result = { field: getattr(self, field) for field in todo_field}
        return result


# Create DB if not exists
db.create_all()

# Decorator Token
def token_required(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        token = request.args.get('token')
        if not token:
            return make_response(jsonify(error={'message': 'Token is required.'}))
        # Decode token
        try:
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except:
            return make_response(jsonify(error={'message': 'Token is invalid.'}))
        return func(*args, **kwargs)
    return decorator

# Get data in token
def get_current_user_from_jwt(jwt_token):
    return jwt.decode(jwt_token, app.config['SECRET_KEY'], algorithms=['HS256'])

# Create token
def create_token(user):
    token = jwt.encode(
        {
            'id': user.id,
            'username': user.name,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=3),
        }, app.config['SECRET_KEY'], algorithm='HS256'
    )
    # Create data user and token then return data
    result = jsonify(
        token = {
            'token': token,
            'message': 'This token you can use to access other url, token will expire in 3 hours.'
        }
    )
    return result

# View
class NameUserList(Resource):
    def get(self):
        all_user = User.query.all()
        list_name = [user.name for user in all_user]
        return make_response(jsonify(names=list_name), 200)

class UserDetail(Resource):
    """
    For get user detail
    """
    @token_required
    def get(self):
        try:
            current_user = get_current_user_from_jwt(request.args.get('token'))
            query = User.query.get_or_404(current_user.get('id'))
        except:
            return make_response(jsonify(error={'message': 'The data you are looking for was not found.'}), 404)
        return make_response(jsonify(data_parser(query, user_field)), 200)
    """
    For login and signup
    """
    def post(self):
        # Status for login or signup
        status_code = 200
        # Get name for form
        _name = request.form.get('name', None)
        # If user not sent name
        if _name is None:
            return make_response(jsonify(error={'message': 'Name is required.'}), 404)
        # Create slug from name
        _slug = slugify(_name)
        _status = request.form.get('status')
        try:
            # If user exists
            user = User.query.filter_by(slug=_slug).first_or_404()
        except:
            # If not exists create new user
            user = User(name=_name, status=_status, slug=_slug)
            user.save()
            status_code = 201
        # If user exists or success create new
        # Create token jwt
        result = create_token(user)
        return make_response(result, status_code)

    """
    Function for update user
    """
    @token_required
    def put(self):
        try:
            current_user = get_current_user_from_jwt(request.args.get('token'))
            query = User.query.get_or_404(current_user['id'])
        except:
            return make_response(jsonify(error={'message': 'The data you are looking for was not found.'}), 404)
        _name = request.form.get('name')
        _status = request.form.get('status')
        if _name is None and _status is None:
            return make_response(jsonify(error={'message': 'Your data is invalid.'}), 400)
        _new_data = {
            'name': _name,
            'status': _status
        }
        # Update data in database if the data sent by the user is not None
        for key, value in _new_data.items():
            if key == 'name' and value is not None:
                setattr(query, key, value)
                setattr(query, 'slug', slugify(value))
            elif value is not None:
                setattr(query, key, value)
            db.session.commit()
        return make_response(jsonify(data_parser(query, user_field)), 200)

    """
    For delete user
    """
    @token_required
    def delete(self):
        try:
            current_user = get_current_user_from_jwt(request.args.get('token'))
            query = User.query.get_or_404(current_user['id'])
        except:
            return make_response(jsonify(error={'message': 'The data you are looking for was not found.'}), 404)
        db.session.delete(query)
        db.session.commit()
        return None, 204

"""
Get List ToDo and Create New ToDo
"""
class TodoList(Resource):
    """
    Get user todo list
    """
    @token_required
    def get(self):
        try:
            current_user = get_current_user_from_jwt(request.args.get('token'))
            query = Todos.query.filter_by(usertodo_id=current_user['id'])
        except:
            return make_response(jsonify(error={'message': 'The data you are looking for was not found.'}), 404)
        result = jsonify(data_parser(query, todo_field, many=True))
        return make_response(result, 200)
    """
    Create new user todo list
    """
    @token_required
    def post(self):
        current_user = get_current_user_from_jwt(request.args.get('token'))
        _activity = request.form.get('activity')
        _date = request.form.get('date')
        if _activity is None and _date is None:
            return make_response(jsonify(error={'message': 'Activity and Date is required'}), 400)
        if _activity is None:
            return make_response(jsonify(error={'message': 'Activity is required'}), 400)
        if _date is None:
            return make_response(jsonify(error={'message': 'Date is required'}), 400)
        _important = request.form.get('important')
        _important = True if _important is not None and _important != 'false' else False
        _completed = request.form.get('completed')
        _completed = True if _completed is not None and _important != 'false' else False
        _user_id = current_user['id']
        todos = Todos(activity=_activity, date=_date, important=_important, completed=_completed, usertodo_id=_user_id)
        todos.save()
        result = jsonify(todos.serialize)
        return make_response(result, 201)

"""
Get ToDo Detail and Update ToDo Detail and Delete ToDo
"""
class TodoDetail(Resource):
    """
    Get detail todo
    """
    @token_required
    def get(self, todoID):
        try:
            current_user = get_current_user_from_jwt(request.args.get('token'))
            query = Todos.query.filter_by(usertodo_id=current_user['id'], id=todoID).first_or_404()
        except:
            return make_response(jsonify(error={'message': 'The data you are looking for was not found.'}), 404)
        result = jsonify(data_parser(query, todo_field))
        return make_response(result, 200)
    """
    Update detail todo
    """
    @token_required
    def put(self, todoID):
        try:
            current_user = get_current_user_from_jwt(request.args.get('token'))
            query = Todos.query.filter_by(usertodo_id=current_user['id'], id=todoID).first_or_404()
        except:
            return make_response(jsonify(error={'message': 'The data you are looking for was not found.'}), 404)
        _activity = request.form.get('activity', None)
        _date = request.form.get('date', None)
        if _date is not None:
            _date = _date.split('-') if _date is not None else _date
            _date = datetime.date(int(_date[0]), int(_date[1]), int(_date[2]))
        _important = request.form.get('important', 'False')
        app.logger.warning(_important)
        _completed = request.form.get('completed', 'False')
        app.logger.warning(_completed)
        _new_data = {
            'activity': _activity,
            'date': _date,
            'important': True if _important.lower() == 'true' else False,
            'completed': True if _completed.lower() == 'true' else False
        }
        app.logger.warning(_new_data['important'])
        app.logger.warning(_new_data['completed'])
        for key, value in _new_data.items():
            if value is not None:
                setattr(query, key, value)
                db.session.commit()
        return make_response(jsonify(data_parser(query, todo_field)), 200)
    """
    Delete one todo
    """
    @token_required
    def delete(self, todoID):
        try:
            current_user = get_current_user_from_jwt(request.args.get('token'))
            query = Todos.query.filter_by(usertodo_id=current_user['id'], id=todoID).first_or_404()
        except:
            return make_response(jsonify(error={'message': 'The data you are looking for was not found.'}), 404)
        db.session.delete(query)
        db.session.commit()
        return None, 204

class TokenRefresh(Resource):
    @token_required
    def get(self):
        current_user = get_current_user_from_jwt(request.args.get('token'))
        query = User.query.get_or_404(current_user.get('id'))
        result = create_token(query)
        return make_response(result, 200)

# Routers
api.add_resource(TokenRefresh, '/api/token', methods=['GET'])
api.add_resource(NameUserList, '/api/names', methods=['GET'])
api.add_resource(UserDetail, '/api/user', methods=['GET', 'POST', 'PUT', 'DELETE'])
api.add_resource(TodoList, '/api/user/todo', methods=['GET', 'POST'])
api.add_resource(TodoDetail, '/api/user/todo/<int:todoID>', methods=['GET', 'PUT', 'DELETE'])

if __name__ == '__main__':
    app.run(debug=True)
