import os
from PIL import Image
from flask import (
        Flask,
        render_template,
        redirect, request,
        url_for,
        flash,
        jsonify,
        g
        )
from resizeimage import resizeimage
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, func, desc
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.orm import scoped_session
from database_setup import Base, User, Category, Item
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
from flask_httpauth import HTTPBasicAuth
import requests

# Images upload folders.
UPLOAD_FOLDER = '/vagrant/item_catalog/static/item_images'
PROFILE_UPLOAD_FOLDER = '/vagrant/item_catalog/static/profile_images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

CLIENT_ID = json.loads(
            open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Item-Catalog"

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
auth = HTTPBasicAuth()

# Connect to Database and create database session
engine = create_engine('sqlite:///catalogitem.db')
Base.metadata.bind = engine

session_factory = sessionmaker(bind=engine)
DBSession = scoped_session(session_factory)
session = DBSession()


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    """
        Facebook third party outh connection.
    """
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = (
            'https://graph.facebook.com/oauth/access_token?'
            'grant_type=fb_exchange_token&client_id={}&client_secret={}&'
            'fb_exchange_token={}'
            ).format(app_id, app_secret, access_token)

    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    """
        Use token to get user info from API
        userinfo_url = "https://graph.facebook.com/v2.8/me"
    """
    token = result.split(',')[0].split(':')[1].replace('"', '')
    url = (
            'https://graph.facebook.com/v2.8/me?'
            'access_token={}&fields=name,id,email'
            ).format(token)

    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    """
        print "url sent for API access:%s"% url
        print "API JSON result: %s" % result
    """
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    login_session['access_token'] = token
    """
        The token must be stored in the login_session in
        order to properly logout
    """
    url = (
            'https://graph.facebook.com/v2.8/me/picture?'
            'access_token={}&redirect=0&height=200&width=200'
            ).format(token)
    """
        Get user picture
    """

    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    user_id = getUserId(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    """
        see if user exists
    """

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ''' " style = "width: 300px;
                    height: 300px;
                    border-radius: 150px;
                    -webkit-border-radius: 150px;
                    -moz-border-radius: 150px;"> '''

    flash("Now logged in as {}".format(login_session['username']))
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/{}/permissions?access_token={}'.format(
            facebook_id,
            access_token
            )
    h = httplib2.Http()
    h.request(url, 'DELETE')[1]
    """
        The access token must me included to successfully logout
    """
    return "you have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    """
        Validate state token
    """
    code = request.data
    """
        Obtain authorization code
    """
    try:
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
        """
            Upgrade the authorization code into a credentials object
        """
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    """
        Check that the access token is valid.
    """
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    if result.get('error') is not None:
        """
            If there was an error in the access token info, abort.
        """
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        """
            Verify that the access token is used for the intended user.
        """
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    if result['issued_to'] != CLIENT_ID:
        """
            Verify that the access token is valid for this app.
        """
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
                json.dumps('Current user is already connected.'),
                200)
        response.headers['Content-Type'] = 'application/json'
        return response

    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id
    """
        Store the access token in the session for later use.
    """

    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['provider'] = 'google'
    """
        Get user info
    """

    user_id = getUserId(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ''' " style = "width: 300px;
                height: 300px;
                border-radius: 150px;
                -webkit-border-radius: 150px;
                -moz-border-radius: 150px;"> '''
    flash("You are now logged in as {}".format(login_session['username']))
    print "done!"
    return output


def getUserId(email):
    """
        Get user id using request filter by email.

        argument:
            email
    """
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except Exception:
        return None


def getUserInfo(user_id):
    """
        Get user info using user id.

        argument:
            user id
    """
    print user_id
    user = session.query(User).filter_by(id=user_id).one()
    return user


# Creats a new user if is not created.
def createUser(login_session):
    """
        Store a user in database.

        argumment:
            login_session
    """
    newUser = User(
            name=login_session['username'],
            email=login_session['email'],
            image=login_session['picture']
            )
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


@app.route('/gdisconnect')
def gdisconnect():
    """
        Google third party oauth disconnect.
        Only disconnect a connected user.
    """
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(
                json.dumps('Failed to revoke token for given user.', 400)
                )
        response.headers['Content-Type'] = 'application/json'
    return response


@app.route('/catalog.json/')
def catalogJSON():
    """
        Creates a JSON reprezention of catalog and
        its categories and their items in  detail.
    """
    categories = session.query(Category).options(
            joinedload(Category.items)
            ).all()
    session.close()
    return jsonify(dict(Category=[
        dict(c.serialize, items=[
            i.serialize for i in c.items
            ]) for c in categories
        ]))


@app.route('/catalog/<path:category_name>/items/JSON')
def categoryItemsJSON(category_name):
    """
        Creates a JSON reprezention of specific category
        and its items.
    """
    category = session.query(Category).filter_by(name=category_name).one()
    items = session.query(Item).filter_by(category=category).all()
    return jsonify(items=[i.serialize for i in items])


@app.route('/catalog/<path:category_name>/<path:item_title>/JSON')
def ItemJSON(category_name, item_title):
    """
        Creates a JSON reprezention of specific item.
    """
    category = session.query(Category).filter_by(name=category_name).one()
    item = session.query(Item).filter_by(
            title=item_title,
            category=category
            ).one()
    return jsonify(item=[item.serialize])


@app.route('/login/', methods=['GET', 'POST'])
def showLogin():
    """
        Create anti-forgery state token or login.
    """
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    print state
    login_session['state'] = state
    if request.method == 'POST':
        print 1
        if 'email' in request.form and 'password' in request.form:
            users = session.query(User).all()
            email = request.form['email']
            password = request.form['password']
            if email in [user.email for user in users]:
                user = session.query(User).filter_by(email=email).one()
                if user.verify_password(password):
                    login_session['provider'] = 'local'
                    login_session['username'] = user.name
                    login_session['email'] = user.email
                    login_session['picture'] = user.image
                    login_session['user_id'] = user.id
                    return redirect(url_for('categoriesDashboard'))
                else:
                    flash('The password is not corect!')
                    return render_template('login.html', STATE=state)
            else:
                flash('{} email is not registred!'.format(email))
                return render_template('login.html', STATE=state)
    return render_template('login.html', STATE=state)


@app.route('/signup/', methods=['GET', 'POST'])
def signUp():
    """
        Sign UP function if there is no third party account.
        Stores the credentials in database.
    """
    users = session.query(User).all()
    if 'email' in request.form and request.method == 'POST':
        email = request.form['email']
        if request.form['email'] in [user.email for user in users]:
            flash('{} is already is registred!'.format(email))
            return render_template('signup.html')
    else:
        flash('Please provide your email address!')
        return render_template('signup.html')

    if 'file' not in request.files and 'image' in request.files:
        image = request.files['image']
        if image.filename != '' and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            if (
                    image.filename in
                    [user.image.split('/')[-1] for user in users]
                    ):
                flash('{} picture name already exists!'.format(image.filename))
                return render_template('signup.html')
            image_resize = Image.open(image)
            image_resize = resizeimage.resize_contain(image_resize, [200, 200])
            image_resize.save(os.path.join(
                app.config['UPLOAD_FOLDER'], filename
                    ), image_resize.format)
            image_path = 'item_images/' + filename
        else:
            image_path = 'profile_images/profile.png'
    else:
        image_path = 'profile_images/profile.png'

    if 'username' in request.form:
        username = request.form['username']
        if username in [user.name for user in users]:
            flash('{} user name already exists!'.format(username))
            return render_template('signup.html')
    else:
        flash('Please choose a user name!')
        return render_template('signup.html')

    if 'password1' in request.form and 'password2' in request.form:
        password1 = request.form['password1']
        password2 = request.form['password2']
        if password1 != password2:
            flash('The password does not match')
            return render_template('signup.html')
    else:
        flash('Please choose a password!')
        return render_template('signup.html')

    user = User(name=username, email=email, image=image_path)
    user.hash_password(password1)
    session.add(user)
    session.commit()
    return redirect(url_for('showLogin'))


@auth.verify_password
def verify_password(email_or_token, password):
    user_id = User.verify_auth_token(email_or_token)
    if user_id:
        user = session.query(User).filter_by(id=user_id).one()
    else:
        user = session.query(User).filter_by(email=email_or_token).first()
        if not user or not user.verify_password(password):
            return False
    g.user = user
    return True


@app.route('/token')
@auth.login_required
def get_auth_token():
    token = g.user.generate_auth_token()
    return jsonify({'token': token.decode('ascii')})


@app.route('/')
def categoriesDashboard():
    """
        Show all categories and last items added.
    """
    categories = session.query(Category).all()
    count = session.query(Category).count()
    items = session.query(Item).order_by(desc('init_time')).limit(count).all()
    for item in items:
        print item.image
    if 'username' not in login_session:
        return render_template(
                'publiccategories.html',
                categories=categories,
                items=items
                )
    else:
        return render_template(
                'categories.html',
                categories=categories,
                items=items,
                user_profile_pic=login_session['picture'],
                login_session_provider=login_session['provider']
                )


@app.route('/catalog/<string:category_name>/items/')
def categoryItems(category_name):
    """
    Page with particular category and its itmes.

    argument:
        category name
    """
    category = session.query(Category).filter_by(name=category_name).one()
    items = session.query(Item).filter_by(
            cat_id=category.id
            ).order_by(desc('init_time'))
    count = session.query(Item).filter_by(
            cat_id=category.id
            ).count()
    if 'username' not in login_session:
        return render_template(
                'items.html',
                category=category,
                items=items,
                count=count
                )
    return render_template(
            'items.html',
            category=category,
            user_profile_pic=login_session['picture'],
            login_session_provider=login_session['provider'],
            items=items,
            count=count
            )


@app.route('/catalog/<string:category_name>/<string:item_title>/')
def itemDescription(category_name, item_title):
    """
        Gives item description.

        arguments:
            category name, item title
    """
    category = session.query(Category).filter_by(name=category_name).one()
    item = session.query(Item).filter_by(
            title=item_title,
            cat_id=category.id
            ).one()
    creator = getUserInfo(item.user_id)
    if ('username' not in login_session or
            creator.id != login_session['user_id']):
        return render_template(
                'publicitemdescription.html',
                category=category,
                item=item
                )
    else:
        return render_template(
                'itemdescription.html',
                user_profile_pic=login_session['picture'],
                login_session_provider=login_session['provider'],
                category=category,
                item=item
                )


def allowed_file(filename):
    """
        Check if the file is allowed by exception.
        Checks ALLOWED_EXTENSIONS
    """
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/catalog/new/', methods=['GET', 'POST'])
def newItem():
    """
        Create new item and store it in database.
    """
    if 'username' not in login_session:
        flash('Please log in')
        return redirect(url_for('showLogin'))
    categories = session.query(Category).all()
    items = session.query(Item).all()
    if request.method == 'POST':
        if 'username' not in login_session:
            flash('Please log in')
            return redirect(url_for('showLogin'))
        if request.form['title'] not in [item.title for item in items]:
            if (
                    request.form['category'] != 'Choose a category...'
                    and request.form['title']
                    ):
                category = session.query(Category).filter_by(
                        name=request.form['category']
                        ).one()
                if 'file' not in request.files and 'image' in request.files:
                    image = request.files['image']
                    if image.filename != '' and allowed_file(image.filename):
                        filename = secure_filename(image.filename)
                        if (image.filename in
                                [item.image.split('/')[-1] for item in items]):
                            flash('{} picture name already exists!'.format(
                                image.filename
                                ))
                            return render_template(
                                    'newitem.html', categories=categories
                                    )
                        image_resize = Image.open(image)
                        image_resize = resizeimage.resize_contain(
                                image_resize, [200, 200]
                                )
                        image_resize.save(os.path.join(
                            app.config['UPLOAD_FOLDER'], filename
                            ), image_resize.format)
                        image_path = 'item_images/' + filename
                    else:
                        image_path = 'item_images/sport-goods.jpg'
                else:
                    image_path = 'item_images/sport-goods.jpg'
                new_item = Item(
                        title=request.form['title'],
                        description=request.form['description'],
                        user_id=login_session['user_id'],
                        image=image_path,
                        cat_id=category.id,
                        init_time=func.now()
                        )
                session.add(new_item)
                session.commit()
                flash('{} item has been created!'.format(
                    request.form['title']
                    ))
                return redirect(url_for('categoriesDashboard'))
            else:
                flash('Please, give a name and pick a category for your item!')
                return render_template(
                        'newitem.html',
                        categories=categories,
                        user_profile_pic=login_session['picture'],
                        login_session_provider=login_session['provider']
                        )
        else:
            flash('{} title already exists!'.format(request.form['title']))
            return render_template(
                    'newitem.html',
                    categories=categories,
                    user_profile_pic=login_session['picture'],
                    login_session_provider=login_session['provider']
                    )
    else:
        return render_template(
                'newitem.html',
                categories=categories,
                user_profile_pic=login_session['picture'],
                login_session_provider=login_session['provider']
                )


@app.route('/catalog/<string:item_title>/edit', methods=['GET', 'POST'])
def editItem(item_title):
    """
        Edit new item and store changes in database.

        argument:
            item title
    """
    edit_item = session.query(Item).filter_by(title=item_title).one()
    category_selected = session.query(Category).filter_by(
            id=edit_item.cat_id
            ).one()
    items = session.query(Item).all()
    categories = session.query(Category).all()
    if 'username' not in login_session:
        flash('Please log in')
        return redirect(url_for('showLogin'))
    if edit_item.user_id != login_session['user_id']:
        flash('Please edit only your items!')
        return redirect(url_for('categoriesDashboard'))
    if request.method == 'POST':
        if request.form['category'] and request.form['title']:
            category_selected = session.query(Category).filter_by(
                    name=request.form['category']
                    ).one()
            if 'file' not in request.files and 'image' in request.files:
                image = request.files['image']
                if image.filename != '' and allowed_file(image.filename):
                    filename = secure_filename(image.filename)
                    if (image.filename in
                            [item.image.split('/')[-1] for item in items]):
                        flash('{} picture name already exists!'.format(
                            image.filename
                            ))
                        return render_template(
                                'newitem.html', categories=categories
                                )
                    image_resize = Image.open(image)
                    image_resize = resizeimage.resize_contain(
                            image_resize, [200, 200]
                            )
                    image_resize.save(os.path.join(
                        app.config['UPLOAD_FOLDER'], filename
                        ), image_resize.format)
                    image_path = 'item_images/' + filename
                else:
                    image_path = 'item_images/sport-goods.jpg'
            else:
                image_path = 'item_images/sport-goods.jpg'
            edit_item.image = image_path
            if request.form['title']:
                edit_item.title = request.form['title']
            if request.form['description']:
                edit_item.description = request.form['description']
            edit_item.cat_id = category_selected.id
            edit_item.init_time = func.now()
            session.add(edit_item)
            session.commit()
            session.close()
            flash('{} item has been successfully edited!'.format(
                request.form['title']
                ))
            return redirect(url_for('categoriesDashboard'))
        else:
            flash('Please choose a title and pick a category!')
            return render_template(
                    'edititem.html',
                    item=edit_item,
                    category_selected=category_selected,
                    user_profile_pic=login_session['picture'],
                    login_session_provider=login_session['provider'],
                    categories=categories
                    )
    else:
        return render_template(
                'edititem.html',
                item=edit_item,
                category_selected=category_selected,
                user_profile_pic=login_session['picture'],
                login_session_provider=login_session['provider'],
                categories=categories
                )


@app.route(
        '/catalog/<string:item_title>/delete/',
        methods=['GET', 'POST']
        )
def deleteItem(item_title):
    """
        Delete item from database and return back to dashboard.

        argument:
            item title
    """
    delete_item = session.query(Item).filter_by(title=item_title).one()
    if 'username' not in login_session:
        flash('Please log in to delete your item')
        return redirect('/login')
    if delete_item.user_id != login_session['user_id']:
        return '''<script>function myFunction() {alert("You're not authorized\
            to delete this item. Please create your own item in order to\
            delete.");}</script><body onload='myFunction()'>'''
    if request.method == 'POST':
        session.delete(delete_item)
        session.commit()
        session.close()
        flash('{} item has been successfully deleted!'.format(
            delete_item.title
            ))
        return redirect(url_for('categoriesDashboard'))
    else:
        return render_template(
                'deleteitem.html',
                user_profile_pic=login_session['picture'],
                login_session_provider=login_session['provider'],
                item=delete_item
                )


@app.route('/disconnect')
def disconnect():
    """
        Disconnect the login session based on provider.
    """
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['access_token']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('categoriesDashboard'))
    else:
        flash("You were not logged in")
        return redirect(url_for('categoriesDashboard'))


if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
