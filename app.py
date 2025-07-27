# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
import sqlite3
import os
import random
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

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
        total_questions INTEGER,
        date_taken TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (exam_id) REFERENCES exams (id)
    )
    ''')
    
    # Insert sample data
    # Add default admin users
    cursor.execute('INSERT OR IGNORE INTO users (username, password, email, role) VALUES (?, ?, ?, ?)',
                  ('admin', generate_password_hash('admin123'), 'admin@example.com', 'admin'))
    cursor.execute('INSERT OR IGNORE INTO users (username, password, email, role) VALUES (?, ?, ?, ?)',
                  ('superadmin', generate_password_hash('super123'), 'superadmin@example.com', 'admin'))
    
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

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first!', 'error')
            return redirect(url_for('login'))
        elif session.get('role') != 'admin':
            flash('You do not have permission to access this page!', 'error')
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

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
            
            # Redirect based on role
            if user[4] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
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
    SELECT r.id, e.title, r.score, r.total_questions, r.date_taken
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
    INSERT INTO results (user_id, exam_id, score, total_questions, date_taken)
    VALUES (?, ?, ?, ?, ?)
    ''', (session['user_id'], session['exam_id'], score, total_questions, datetime.now()))
    
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
    SELECT r.id, e.title, r.score, r.total_questions, r.date_taken
    FROM results r
    JOIN exams e ON r.exam_id = e.id
    WHERE r.user_id = ?
    ORDER BY r.date_taken DESC
    ''', (session['user_id'],))
    results = cursor.fetchall()
    
    conn.close()
    
    return render_template('results.html', results=results)

# Admin routes
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = sqlite3.connect('exam_system.db')
    cursor = conn.cursor()
    
    # Get total number of users
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "student"')
    total_students = cursor.fetchone()[0]
    
    # Get total number of exams
    cursor.execute('SELECT COUNT(*) FROM exams')
    total_exams = cursor.fetchone()[0]
    
    # Get total number of questions
    cursor.execute('SELECT COUNT(*) FROM questions')
    total_questions = cursor.fetchone()[0]
    
    # Get total number of results/attempts
    cursor.execute('SELECT COUNT(*) FROM results')
    total_attempts = cursor.fetchone()[0]
    
    # Get recent exam results
    cursor.execute('''
    SELECT u.username, e.title, r.score, r.total_questions, r.date_taken
    FROM results r
    JOIN users u ON r.user_id = u.id
    JOIN exams e ON r.exam_id = e.id
    ORDER BY r.date_taken DESC
    LIMIT 10
    ''')
    recent_results = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin/dashboard.html', 
                          total_students=total_students,
                          total_exams=total_exams,
                          total_questions=total_questions,
                          total_attempts=total_attempts,
                          recent_results=recent_results)

@app.route('/admin/exams')
@admin_required
def admin_exams():
    conn = sqlite3.connect('exam_system.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM exams')
    exams = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin/exams.html', exams=exams)

@app.route('/admin/exams/add', methods=['GET', 'POST'])
@admin_required
def admin_add_exam():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        time_limit = request.form['time_limit']
        
        conn = sqlite3.connect('exam_system.db')
        cursor = conn.cursor()
        
        cursor.execute('INSERT INTO exams (title, description, time_limit) VALUES (?, ?, ?)',
                      (title, description, time_limit))
        exam_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        flash('Exam added successfully!', 'success')
        return redirect(url_for('admin_edit_exam', exam_id=exam_id))
        
    return render_template('admin/add_exam.html')

@app.route('/admin/exams/edit/<int:exam_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_exam(exam_id):
    conn = sqlite3.connect('exam_system.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        time_limit = request.form['time_limit']
        
        cursor.execute('UPDATE exams SET title = ?, description = ?, time_limit = ? WHERE id = ?',
                     (title, description, time_limit, exam_id))
        conn.commit()
        
        flash('Exam updated successfully!', 'success')
    
    # Get exam details
    cursor.execute('SELECT * FROM exams WHERE id = ?', (exam_id,))
    exam = cursor.fetchone()
    
    # Get exam questions
    cursor.execute('SELECT * FROM questions WHERE exam_id = ?', (exam_id,))
    questions = cursor.fetchall()
    
    conn.close()
    
    if not exam:
        flash('Exam not found!', 'error')
        return redirect(url_for('admin_exams'))
        
    return render_template('admin/edit_exam.html', exam=exam, questions=questions)

@app.route('/admin/exams/delete/<int:exam_id>')
@admin_required
def admin_delete_exam(exam_id):
    conn = sqlite3.connect('exam_system.db')
    cursor = conn.cursor()
    
    # Delete associated questions
    cursor.execute('DELETE FROM questions WHERE exam_id = ?', (exam_id,))
    
    # Delete associated results
    cursor.execute('DELETE FROM results WHERE exam_id = ?', (exam_id,))
    
    # Delete the exam
    cursor.execute('DELETE FROM exams WHERE id = ?', (exam_id,))
    
    conn.commit()
    conn.close()
    
    flash('Exam deleted successfully!', 'success')
    return redirect(url_for('admin_exams'))

@app.route('/admin/questions/add/<int:exam_id>', methods=['POST'])
@admin_required
def admin_add_question(exam_id):
    question_text = request.form['question_text']
    option_a = request.form['option_a']
    option_b = request.form['option_b']
    option_c = request.form['option_c']
    option_d = request.form['option_d']
    correct_answer = request.form['correct_answer']
    
    conn = sqlite3.connect('exam_system.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO questions (exam_id, question_text, option_a, option_b, option_c, option_d, correct_answer)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (exam_id, question_text, option_a, option_b, option_c, option_d, correct_answer))
    
    conn.commit()
    conn.close()
    
    flash('Question added successfully!', 'success')
    return redirect(url_for('admin_edit_exam', exam_id=exam_id))

@app.route('/admin/questions/delete/<int:question_id>')
@admin_required
def admin_delete_question(question_id):
    conn = sqlite3.connect('exam_system.db')
    cursor = conn.cursor()
    
    # Get the exam_id before deleting
    cursor.execute('SELECT exam_id FROM questions WHERE id = ?', (question_id,))
    result = cursor.fetchone()
    
    if not result:
        flash('Question not found!', 'error')
        return redirect(url_for('admin_exams'))
        
    exam_id = result[0]
    
    # Delete the question
    cursor.execute('DELETE FROM questions WHERE id = ?', (question_id,))
    
    conn.commit()
    conn.close()
    
    flash('Question deleted successfully!', 'success')
    return redirect(url_for('admin_edit_exam', exam_id=exam_id))

@app.route('/admin/students')
@admin_required
def admin_students():
    conn = sqlite3.connect('exam_system.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE role = "student"')
    students = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin/students.html', students=students)

@app.route('/admin/students/delete/<int:student_id>')
@admin_required
def admin_delete_student(student_id):
    conn = sqlite3.connect('exam_system.db')
    cursor = conn.cursor()
    
    # Delete associated results
    cursor.execute('DELETE FROM results WHERE user_id = ?', (student_id,))
    
    # Delete the student
    cursor.execute('DELETE FROM users WHERE id = ? AND role = "student"', (student_id,))
    
    conn.commit()
    conn.close()
    
    flash('Student deleted successfully!', 'success')
    return redirect(url_for('admin_students'))

@app.route('/admin/results')
@admin_required
def admin_results():
    conn = sqlite3.connect('exam_system.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT r.id, u.username, e.title, r.score, r.total_questions, r.date_taken
    FROM results r
    JOIN users u ON r.user_id = u.id
    JOIN exams e ON r.exam_id = e.id
    ORDER BY r.date_taken DESC
    ''')
    results = cursor.fetchall()
    
    conn.close()
    
    return render_template('admin/results.html', results=results)

@app.route('/admin/results/delete/<int:result_id>')
@admin_required
def admin_delete_result(result_id):
    conn = sqlite3.connect('exam_system.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM results WHERE id = ?', (result_id,))
    
    conn.commit()
    conn.close()
    
    flash('Result deleted successfully!', 'success')
    return redirect(url_for('admin_results'))

if __name__ == '__main__':
    app.run(debug=True)