from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'ваш_секретный_ключ'  # Замените на случайную строку


# Создаем базу данных, если она не существует
def init_db():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    # Создаем таблицу пользователей
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Создаем таблицу задач
    c.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        category TEXT,
        priority TEXT,
        due_date DATE,
        status TEXT DEFAULT "Новая",
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    conn.commit()
    conn.close()


init_db()


# Маршруты для авторизации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()

        # Проверяем, существует ли пользователь
        c.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if c.fetchone():
            conn.close()
            flash('Пользователь с таким именем или email уже существует!')
            return redirect(url_for('register'))

        # Хешируем пароль и сохраняем пользователя
        password_hash = generate_password_hash(password)
        c.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                  (username, password_hash, email))
        conn.commit()
        conn.close()

        flash('Регистрация успешна! Теперь вы можете войти.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()

        c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            return redirect(url_for('dashboard'))

        flash('Неверное имя пользователя или пароль!')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('login'))


# Маршруты для работы с задачами
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    c.execute("""
    SELECT id, title, category, priority, due_date, status 
    FROM tasks 
    WHERE user_id = ? 
    ORDER BY 
        CASE status 
            WHEN 'Завершена' THEN 2
            ELSE 1
        END,
        CASE priority
            WHEN 'Высокий' THEN 1
            WHEN 'Средний' THEN 2
            WHEN 'Низкий' THEN 3
            ELSE 4
        END,
        due_date
    """, (session['user_id'],))

    tasks = c.fetchall()
    conn.close()

    return render_template('dashboard.html', tasks=tasks)


@app.route('/task/new', methods=['GET', 'POST'])
def new_task():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        priority = request.form['priority']
        due_date = request.form['due_date'] if request.form['due_date'] else None

        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()

        c.execute("""
        INSERT INTO tasks (user_id, title, description, category, priority, due_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (session['user_id'], title, description, category, priority, due_date))

        conn.commit()
        conn.close()

        flash('Задача успешно создана!')
        return redirect(url_for('dashboard'))

    return render_template('new_task.html')


@app.route('/task/<int:task_id>')
def view_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    c.execute("""
    SELECT id, title, description, category, priority, due_date, status, created_at
    FROM tasks 
    WHERE id = ? AND user_id = ?
    """, (task_id, session['user_id']))

    task = c.fetchone()
    conn.close()

    if not task:
        flash('Задача не найдена!')
        return redirect(url_for('dashboard'))

    return render_template('view_task.html', task=task)


@app.route('/task/<int:task_id>/edit', methods=['GET', 'POST'])
def edit_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        priority = request.form['priority']
        due_date = request.form['due_date'] if request.form['due_date'] else None
        status = request.form['status']

        c.execute("""
        UPDATE tasks 
        SET title = ?, description = ?, category = ?, priority = ?, due_date = ?, status = ?
        WHERE id = ? AND user_id = ?
        """, (title, description, category, priority, due_date, status, task_id, session['user_id']))

        conn.commit()
        flash('Задача обновлена!')
        return redirect(url_for('view_task', task_id=task_id))

    c.execute("""
    SELECT id, title, description, category, priority, due_date, status
    FROM tasks 
    WHERE id = ? AND user_id = ?
    """, (task_id, session['user_id']))

    task = c.fetchone()
    conn.close()

    if not task:
        flash('Задача не найдена!')
        return redirect(url_for('dashboard'))

    return render_template('edit_task.html', task=task)


@app.route('/task/<int:task_id>/delete', methods=['POST'])
def delete_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    c.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, session['user_id']))
    conn.commit()
    conn.close()

    flash('Задача удалена!')
    return redirect(url_for('dashboard'))


@app.route('/tasks/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    # Статистика по категориям
    c.execute("""
    SELECT category, COUNT(*) as count
    FROM tasks
    WHERE user_id = ?
    GROUP BY category
    """, (session['user_id'],))
    categories = c.fetchall()

    # Статистика по приоритетам
    c.execute("""
    SELECT priority, COUNT(*) as count
    FROM tasks
    WHERE user_id = ?
    GROUP BY priority
    """, (session['user_id'],))
    priorities = c.fetchall()

    # Статистика по статусам
    c.execute("""
    SELECT status, COUNT(*) as count
    FROM tasks
    WHERE user_id = ?
    GROUP BY status
    """, (session['user_id'],))
    statuses = c.fetchall()

    conn.close()

    return render_template('analytics.html',
                           categories=categories,
                           priorities=priorities,
                           statuses=statuses)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
