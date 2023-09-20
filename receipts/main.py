from flask import Flask, render_template, request, session 
from flask import redirect, url_for, flash, get_flashed_messages
import json
from hashlib import sha256
import fileinput
from datetime import datetime


# Это callable WSGI-приложение
app = Flask(__name__)
app.config['SECRET_KEY'] = 'Secret'


#@app.route('/')
#def route():
#    messages = get_flashed_messages(with_categories=True)
#    current_user = session.get('user')
#    return render_template(
#        'html/main/index.html',
#        messages=messages,
#        current_user=current_user,
#        )


@app.get('/')
def books_get():
    search_word = request.args.get('term', default=None)
    current_user = session.get('user')

    with open('books.txt', 'r') as repo, open('users.txt', 'r') as users:
        authors = []
        books = [json.loads(r) for r in repo.readlines()]
        users = [json.loads(r) for r in users.readlines()]

        filtered_books, search_word = search(books, search_word)
        for f_book in filtered_books:
            authors.append(find(f_book['user'], users))

        messages = get_flashed_messages(with_categories=True)
        print(messages)

        return render_template(
            'html/main/index.html',
            books=filtered_books,
            search=search_word,
            messages=messages,
            iterables=zip(filtered_books,authors),
            user=current_user
        )


@app.get('/books/<id>')
def book_get(id):
    messages = get_flashed_messages(with_categories=True)
    current_user = session.get('user')
    with open('books.txt', 'r') as repo:
        with open('users.txt', 'r') as users:
            books = [json.loads(r) for r in repo.readlines()]
            users = [json.loads(r) for r in users.readlines()]
            book = find(id, books)
            author = find(book['user'], users)
            if book:
                return render_template(
                    'html/books/show.html',
                    current_user=current_user,
                    book=book,
                    author=author,
                    messages=messages
                    )
            return render_template('html/main/404.html'), 404


@app.post('/books/')
def book_post():
    current_user = session.get('user')

    with open('books.txt', 'a') as repo:
        book = request.form.to_dict()

        errors = validate(book, type='book')

        if errors:
            return render_template(
                'html/books/new_book.html',
            book=book,
            errors=errors
            ), 422

        book['id'] = generate_id('books.txt') # type: ignore
        book['user'] = current_user['id']
        book['time_created'] = str(datetime.now())
        repo.write(json.dumps(book))
        repo.write("\n")
        flash('Book has been added', 'success')

        return redirect(url_for('books_get'), code=302)
    

@app.get('/books/new')
def book_create():
    book = {'name': '', 'summary': '', 'ingredients': '', 'image': ""}
    errors = []
    return render_template(
        'html/books/new_book.html',
        book=book,
        errors=errors)


@app.get('/books/<id>/edit')
def book_edit(id):
    with open('books.txt', 'r') as repo:
        books = [json.loads(r) for r in repo.readlines()]
        errors = []
        book = find(id, books)
        if book:
            return render_template(
                'html/books/edit.html',
                book=book,
                errors=errors
                )
        return render_template('html/main/404.html'), 404


@app.post('/books/<id>/patch')
def book_patch(id):
    current_user = session.get('user')
    data = request.form.to_dict()
    errors = validate(data, type='book')

    if errors:
        with open('books.txt', 'r') as repo:
            books = [json.loads(r) for r in repo.readlines()]
            book = find(id, books)

            return render_template(
                'html/books/edit.html',
                book=book,
                errors=errors,
                ), 422
    
    data['id'] = int(id)
    data['user'] = current_user['id']
    replace_line('books.txt', id, data)

    flash('Book has been successfully updated!', 'success')

    return redirect(url_for('book_get', id=id))


@app.post('/books/<id>/delete')
def book_delete(id):
    replace_line('books.txt', id, None)

    flash('Book has been deleted', 'success')
    return redirect(url_for('books_get'))


@app.post('/session/new')
def new_session():
    data = request.form.to_dict()
    with open('users.txt', 'r') as repo:
        users = [json.loads(r) for r in repo.readlines()]
        user = get_user(data, users)

        if user:
            session['user'] = user
            return redirect(url_for('route'))
        else:
            flash('Wrong password or name.')
            return redirect(url_for('route'))


@app.get('/users/<id>')
def user_get(id):
    messages = get_flashed_messages(with_categories=True)
    current_user = session.get('user')
    with open('books.txt', 'r') as repo:
        with open('users.txt', 'r') as users:
            books = [json.loads(r) for r in repo.readlines()]
            users = [json.loads(r) for r in users.readlines()]
            user = find(id, users)
            recipes = []
            for book in books:
                recipes.append(find(user['id'], books, data_id='user'))

            if user:
                return render_template(
                    'html/users/show.html',
                    user=user,
                    books=recipes,
                    messages=messages,
                    current_user=current_user,
                    author=user
                    )
            return render_template('html/main/404.html'), 404


@app.post('/users/')
def users_post():
    with open('users.txt', 'a') as repo:
        user = request.form.to_dict()

        errors = validate(user, type='user')

        if errors:
            return render_template(
                'html/main/new_user.html',
            user=user,
            errors=errors
            ), 422

        user['id'] = generate_id('users.txt') # type: ignore
        user['password'] = encode_password(user['password'])
        repo.write(json.dumps(user))
        repo.write("\n")
        flash('Congrats on creating a user profile!', 'success')

        return redirect(url_for('books_get'), code=302)
    

@app.get('/users/')
def user_create():
    user = {'name': '', 'password': ''}
    errors = []
    return render_template(
        'html/main/new_user.html',
        user=user,
        errors=errors)


@app.get('/users/<id>/edit')
def user_edit(id):
    current_user = session.get('user')
    with open('users.txt', 'r') as repo:
        users = [json.loads(r) for r in repo.readlines()]
        errors = []
        user = find(id, users)
        if user['id'] == current_user['id']:
            return render_template(
                'html/users/settings.html',
                user=user,
                errors=errors
                )
        return render_template('html/main/404.html'), 404


@app.post('/users/<id>/patch')
def user_patch(id):
    current_user = session.get('user')
    data = request.form.to_dict()
    errors = validate(data, type='user')

    if errors:
        with open('users.txt', 'r') as repo:
            users = [json.loads(r) for r in repo.readlines()]
            user = find(id, users)

            return render_template(
                'html/books/settings.html',
                user=user,
                errors=errors,
                ), 422
    
    data['id'] = int(id)
#    data['user'] = current_user['id']
    replace_line('users.txt', id, data)

    flash('Your profile has been successfully updated!', 'success')

    return redirect(url_for('book_get', id=id))


@app.route('/session/delete', methods=['DELETE', 'POST'])
def delete_session():
    session.clear()
    return redirect(url_for('books_get'))


@app.errorhandler(404)
def not_found(e):
    return render_template("html/main/404.html")


def generate_id(file):
    with open(file, 'r') as repo:
        try:
            return json.loads(repo.readlines()[-1])['id'] + 1
        except IndexError:
            return 0
        

def search(data, search_word):
    search_word = request.args.get('term', default=None)
    if search_word is None:
        filtered_data = data
        search_word = ''
    else:
        filtered_data = [
            u for u in data if (
                search_word.lower() in u['name'].lower() or
                search_word.lower() in u['summary'].lower())
                ]
    return filtered_data, search_word


def validate(data, type):
    errors = {}
    if type == 'book':
        if len(data['name']) == 0:
            errors['name'] = "Поле не может быть пустым"
        if len(data['summary']) < 100:
            errors['summary'] = "Рецепт должен содержать хотя бы 100 символов!"
    elif type == 'user':
        if len(data['name']) == 0:
            errors['name'] = "Поле не может быть пустым"
        if len(data['password']) < 5:
            errors['password'] = "Пароль должен содержать хотя бы 5 символов"
        if any(char.isdigit() for char in data['password']) is False:
            errors['password'] = "Пароль должен содержать хотя бы одну цифру"
    return errors 

def find(id, data, data_id='id'):
    for d in data:
        if int(d[data_id]) == int(id):
            return d
    return False

def replace_line(file, id, new_content):
    # temporary function for editing the content in txt file by 
    # overwriting the entire file.
    # To be replaced with the proper database
    if new_content is not None:
        with fileinput.input(file, inplace=True) as file:
            for line in file:
                if json.loads(line)['id'] == int(id):
                    print(json.dumps(new_content))
                else:
                    print(line.rstrip())
    else:
        with fileinput.input(file, inplace=True) as file:
            for line in file:
                if json.loads(line.strip())['id'] != int(id):
                    print(line.rstrip())
            print("\n")


def encode_password(password):
    return sha256(password.encode()).hexdigest()


def get_user(form_data, repo):
    name = form_data['name']
    password = encode_password(form_data['password'])
    for user in repo:
        if user['name'] == name and user['password'] == password:
            return user