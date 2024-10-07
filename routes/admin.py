# admin.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from models import db, User, Student, Teacher, Class, Book, BorrowHistory
from werkzeug.security import generate_password_hash
from functools import wraps
from datetime import datetime


admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin')
@admin_required
def admin_dashboard():
    classes = Class.query.all()
    teachers = Teacher.query.all()
    students = Student.query.all()
    books = Book.query.all()
    return render_template('admin_dashboard.html', classes=classes, teachers=teachers, students=students, books=books)

@admin_bp.route('/add_class', methods=['GET', 'POST'])
@admin_required
def add_class():
    if request.method == 'POST':
        class_name = request.form['name']
        existing_class = Class.query.filter_by(name=class_name).first()
        if existing_class:
            flash('Class with that name already exists.', 'danger')
            return redirect(url_for('admin.add_class'))
        new_class = Class(name=class_name)
        db.session.add(new_class)
        db.session.commit()
        flash(f'Class "{class_name}" has been created successfully!', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    return render_template('add_class.html')

@admin_bp.route('/add_teacher', methods=['GET', 'POST'])
@admin_required
def add_teacher():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        class_id = request.form['class_id']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.', 'danger')
            return redirect(url_for('admin.add_teacher'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password, role='teacher')
        db.session.add(new_user)
        db.session.commit()

        new_teacher = Teacher(user_id=new_user.id, name=name)
        db.session.add(new_teacher)
        db.session.commit()

        class_ = Class.query.get(class_id)
        if class_:
            new_teacher.classes.append(class_)
            db.session.commit()
            flash(f'Teacher "{name}" has been added and assigned to class "{class_.name}" successfully!', 'success')
        else:
            flash('Invalid class selected.', 'danger')

        return redirect(url_for('admin.admin_dashboard'))

    classes = Class.query.all()
    return render_template('add_teacher.html', classes=classes)

@admin_bp.route('/add_student', methods=['GET', 'POST'])
@admin_required
def add_student():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        class_id = request.form['class_id']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.', 'danger')
            return redirect(url_for('admin.add_student'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password, role='student')
        db.session.add(new_user)
        db.session.commit()

        new_student = Student(user_id=new_user.id, name=name)
        db.session.add(new_student)
        db.session.commit()

        class_ = Class.query.get(class_id)
        if class_:
            new_student.classes.append(class_)
            db.session.commit()
            flash(f'Student "{name}" has been added and assigned to class "{class_.name}" successfully!', 'success')
        else:
            flash('Invalid class selected.', 'danger')

        return redirect(url_for('admin.admin_dashboard'))

    classes = Class.query.all()
    return render_template('add_student.html', classes=classes)

@admin_bp.route('/assign_teacher', methods=['GET', 'POST'])
@admin_required
def assign_teacher():
    if request.method == 'POST':
        class_id = request.form['class_id']
        teacher_id = request.form['teacher_id']
        class_ = Class.query.get(class_id)
        teacher = Teacher.query.get(teacher_id)
        if not class_ or not teacher:
            flash('Invalid class or teacher selection.', 'danger')
            return redirect(url_for('admin.assign_teacher'))
        if teacher in class_.teachers:
            flash('Teacher is already assigned to this class.', 'danger')
        else:
            class_.teachers.append(teacher)
            db.session.commit()
            flash(f'Teacher "{teacher.name}" assigned to class "{class_.name}" successfully!', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    classes = Class.query.all()
    teachers = Teacher.query.all()
    return render_template('assign_teacher.html', classes=classes, teachers=teachers)

@admin_bp.route('/assign_student', methods=['GET', 'POST'])
@admin_required
def assign_student():
    if request.method == 'POST':
        class_id = request.form['class_id']
        student_id = request.form['student_id']
        class_ = Class.query.get(class_id)
        student = Student.query.get(student_id)
        if not class_ or not student:
            flash('Invalid class or student selection.', 'danger')
            return redirect(url_for('admin.assign_student'))
        if student in class_.students:
            flash('Student is already assigned to this class.', 'danger')
        else:
            class_.students.append(student)
            db.session.commit()
            flash(f'Student "{student.name}" assigned to class "{class_.name}" successfully!', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    classes = Class.query.all()
    students = Student.query.all()
    return render_template('assign_student.html', classes=classes, students=students)


@admin_bp.route('/delete_class/<int:class_id>', methods=['POST'])
@admin_required
def delete_class(class_id):
    class_ = Class.query.get_or_404(class_id)
    try:
        db.session.delete(class_)
        db.session.commit()
        flash(f'Class "{class_.name}" has been deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting class: {str(e)}', 'danger')
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/delete_teacher/<int:teacher_id>', methods=['POST'])
@admin_required
def delete_teacher(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)

    # Access the associated user through the 'user' relationship, not 'user_profile'
    user = teacher.user

    if user:
        db.session.delete(user)  # Delete the associated user record
    db.session.delete(teacher)  # Delete the teacher record
    db.session.commit()

    flash(f'Teacher "{teacher.name}" has been deleted.', 'success')
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/delete_student/<int:student_id>', methods=['POST'])
@admin_required
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    user = student.user
    try:
        db.session.delete(student)
        db.session.delete(user)
        db.session.commit()
        flash(f'Student "{student.name}" has been deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting student: {str(e)}', 'danger')
    return redirect(url_for('admin.admin_dashboard'))
    
    
@admin_bp.route('/delete_book/<int:book_id>', methods=['POST'])
@admin_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    try:
        db.session.delete(book)
        db.session.commit()
        flash('Book deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting book: {e}', 'danger')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/unassign_student/<int:class_id>/<int:student_id>', methods=['POST'])
@admin_required
def unassign_student(class_id, student_id):
    class_ = Class.query.get_or_404(class_id)
    student = Student.query.get_or_404(student_id)

    if student not in class_.students:
        flash(f'Student "{student.name}" is not assigned to class "{class_.name}".', 'danger')
    else:
        try:
            class_.students.remove(student)
            db.session.commit()
            flash(f'Student "{student.name}" has been unassigned from class "{class_.name}".', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error unassigning student: {str(e)}', 'danger')

    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/unassign_teacher/<int:class_id>/<int:teacher_id>', methods=['POST'])
@admin_required
def unassign_teacher(class_id, teacher_id):
    class_ = Class.query.get_or_404(class_id)
    teacher = Teacher.query.get_or_404(teacher_id)

    if teacher not in class_.teachers:
        flash(f'Teacher "{teacher.name}" is not assigned to class "{class_.name}".', 'danger')
    else:
        try:
            class_.teachers.remove(teacher)
            db.session.commit()
            flash(f'Teacher "{teacher.name}" has been unassigned from class "{class_.name}".', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error unassigning teacher: {str(e)}', 'danger')

    return redirect(url_for('admin.admin_dashboard'))
