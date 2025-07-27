# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
import random
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database setup
def init_db():
    conn = sqlite3.connect('exam_system.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        role TEXT DEFAULT 'student'
    )
    ''')
    
    # Create exams table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        time_limit INTEGER DEFAULT 30
    )
    ''')
    
    # Create questions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER,
        question_text TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        correct_answer TEXT NOT NULL,
        FOREIGN KEY (exam_id) REFERENCES exams (id)
    )
    ''')
    
    # Create results table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        exam_id INTEGER,
        score INTEGER,
        date_taken TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (exam_id) REFERENCES exams (id)
    )
    ''')
    
    # Insert sample data
    # Add an admin user
    cursor.execute('INSERT OR IGNORE INTO users (username, password, email, role) VALUES (?, ?, ?, ?)',
                  ('admin', generate_password_hash('admin123'), 'admin@example.com', 'admin'))
    
    # Add a sample exam
    cursor.execute('INSERT OR IGNORE INTO exams (id, title, description, time_limit) VALUES (?, ?, ?, ?)',
                  (1, 'Python Basics', 'Test your knowledge of Python fundamentals', 10))
    
    # Add sample questions
    sample_questions = [
        (1, 'What is Python?', 'A snake', 'A programming language', 'A game', 'A food', 'B'),
        (1, 'Which of the following is not a Python data type?', 'List', 'Dictionary', 'Tuple', 'Array', 'D'),
        (1, 'What is the output of print(2 + 2)?', '4', '22', 'Error', 'None', 'A'),
        (1, 'Which of these is used to define a function in Python?', 'function', 'def', 'define', 'func', 'B'),
        (1, 'What symbol is used for comments in Python?', '//', '#', '--', '/*', 'B')
    ]
    
    for q in sample_questions:
        cursor.execute('INSERT OR IGNORE INTO questions (exam_id, question_text, option_a, option_b, option_c, option_d, correct_answer) VALUES (?, ?, ?, ?, ?, ?, ?)', q)
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        conn = sqlite3.connect('exam_system.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO users (username, password, email) VALUES (?, ?, ?)',
                          (username, generate_password_hash(password), email))
            conn.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists!', 'error')
        finally:
            conn.close()
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('exam_system.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[4]
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('exam_system.db')
    cursor = conn.cursor()
    
    # Get available exams
    cursor.execute('SELECT * FROM exams')
    exams = cursor.fetchall()
    
    # Get user's results
    cursor.execute('''
    SELECT r.id, e.title, r.score, r.date_taken
    FROM results r
    JOIN exams e ON r.exam_id = e.id
    WHERE r.user_id = ?
    ORDER BY r.date_taken DESC
    ''', (session['user_id'],))
    results = cursor.fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', exams=exams, results=results)

@app.route('/exam/<int:exam_id>')
def take_exam(exam_id):
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('exam_system.db')
    cursor = conn.cursor()
    
    # Get exam details
    cursor.execute('SELECT * FROM exams WHERE id = ?', (exam_id,))
    exam = cursor.fetchone()
    
    if not exam:
        flash('Exam not found!', 'error')
        return redirect(url_for('dashboard'))
    
    # Get exam questions
    cursor.execute('SELECT * FROM questions WHERE exam_id = ?', (exam_id,))
    questions = cursor.fetchall()
    
    conn.close()
    
    # Shuffle questions
    random.shuffle(questions)
    
    # Store exam time limit in session
    session['exam_time'] = exam[3] * 60  # convert minutes to seconds
    session['exam_id'] = exam_id
    
    return render_template('exam.html', exam=exam, questions=questions)

@app.route('/submit_exam', methods=['POST'])
def submit_exam():
    if 'user_id' not in session or 'exam_id' not in session:
        flash('Invalid session!', 'error')
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect('exam_system.db')
    cursor = conn.cursor()
    
    # Get all questions for the exam
    cursor.execute('SELECT id, correct_answer FROM questions WHERE exam_id = ?', (session['exam_id'],))
    questions = cursor.fetchall()
    
    score = 0
    total_questions = len(questions)
    
    # Calculate score
    for question in questions:
        q_id = question[0]
        correct_answer = question[1]
        user_answer = request.form.get(f'question_{q_id}', '')
        
        if user_answer == correct_answer:
            score += 1
    
    # Save result
    cursor.execute('''
    INSERT INTO results (user_id, exam_id, score, date_taken)
    VALUES (?, ?, ?, ?)
    ''', (session['user_id'], session['exam_id'], score, datetime.now()))
    
    conn.commit()
    conn.close()
    
    percentage = (score / total_questions) * 100 if total_questions > 0 else 0
    
    flash(f'Exam submitted! Your score: {score}/{total_questions} ({percentage:.1f}%)', 'success')
    return redirect(url_for('dashboard'))

@app.route('/results')
def view_results():
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('exam_system.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT r.id, e.title, r.score, r.date_taken
    FROM results r
    JOIN exams e ON r.exam_id = e.id
    WHERE r.user_id = ?
    ORDER BY r.date_taken DESC
    ''', (session['user_id'],))
    results = cursor.fetchall()
    
    conn.close()
    
    return render_template('results.html', results=results)

if __name__ == '__main__':
    app.run(debug=True)
