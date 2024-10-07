# teacher.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, jsonify
from models import db, User, Teacher, Class, Book, BorrowHistory, DonationRequest, Student
from functools import wraps
from datetime import datetime
import os, requests
from werkzeug.utils import secure_filename

teacher_bp = Blueprint('teacher', __name__, template_folder='templates')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'teacher':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@teacher_bp.route('/teacher')
@teacher_required
def teacher_dashboard():
    user = User.query.get(session['user_id'])
    teacher = user.teacher_profile

    # Fetch all classes the teacher is assigned to
    teacher_classes = teacher.classes

    # If there's only one class, we can directly use it, else the user needs to select one
    selected_class = teacher_classes[0] if len(teacher_classes) == 1 else None

    # Initialize collections for students, books, requests, borrows, and donations
    students = []
    books = []
    pending_requests = []
    active_borrows = []
    pending_donations = []

    # If the teacher has more than one class, allow selecting a class via a dropdown
    if not selected_class and 'class_id' in request.args:
        selected_class = Class.query.get(request.args.get('class_id'))

    # If selected_class exists, gather data
    if selected_class:
        students = selected_class.students
        books = Book.query.filter_by(class_id=selected_class.id).all()

        # Gather pending borrow requests for the current class
        pending_requests = BorrowHistory.query.filter(
            BorrowHistory.borrow_date == None,
            BorrowHistory.book.has(class_id=selected_class.id),
            ~BorrowHistory.status.contains('Rejected')
        ).all()

        # Gather active borrows for the current class
        active_borrows = BorrowHistory.query.filter(
            BorrowHistory.borrow_date != None,
            BorrowHistory.return_date == None,
            BorrowHistory.book.has(class_id=selected_class.id)
        ).all()

        # Gather pending donation requests for the current class
        pending_donations = DonationRequest.query.filter_by(
            status="Pending approval",
            class_id=selected_class.id
        ).all()

    return render_template('teacher_dashboard.html',
                           students=students,
                           books=books,
                           pending_requests=pending_requests,
                           active_borrows=active_borrows,
                           pending_donations=pending_donations,
                           teacher_classes=teacher_classes,
                           selected_class=selected_class)



# API to get pending requests (for AJAX polling)
@teacher_bp.route('/api/pending_requests')
@teacher_required
def get_pending_requests():
    user = User.query.get(session['user_id'])
    teacher = user.teacher_profile
    teacher_class = teacher.classes[0]  # Assume teacher is assigned to one class for simplicity

    # Get only pending borrow requests
    pending_borrow_requests = BorrowHistory.query.filter(
        BorrowHistory.borrow_date == None,  # Only requests with no borrow date
        BorrowHistory.book.has(class_id=teacher_class.id)
    ).all()

    # Get only pending donation requests
    pending_donation_requests = DonationRequest.query.filter_by(
        status="Pending approval",  # Only requests pending approval
        class_id=teacher_class.id
    ).all()

    # Return the data in JSON format with request_id and other relevant info
    return jsonify({
        'borrow_requests': [
            {
                'request_id': request.id,
                'book_title': request.book.title,
                'student_name': request.student.name,
                'class_name': teacher_class.name,
                'request_date': request.borrow_date.strftime('%Y-%m-%d') if request.borrow_date else 'N/A'
            }
            for request in pending_borrow_requests
        ],
        'donation_requests': [
            {
                'request_id': request.id,
                'book_title': request.title,
                'student_name': request.student.name,
                'class_name': teacher_class.name,
                'request_date': request.submitted_at.strftime('%Y-%m-%d') if request.submitted_at else 'N/A'
            }
            for request in pending_donation_requests
        ]
    })


@teacher_bp.route('/delete_book/<int:book_id>', methods=['POST'])
@teacher_required
def delete_book(book_id):
    user = User.query.get(session['user_id'])
    teacher = user.teacher_profile
    teacher_class = teacher.classes[0]

    book = Book.query.get_or_404(book_id)

    if book.class_id != teacher_class.id:
        flash('You cannot delete books outside your class.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    try:
        # Remove the cover image file if it exists
        if book.cover_filename:
            cover_path = os.path.join(current_app.config['UPLOAD_FOLDER'], book.cover_filename)
            if os.path.exists(cover_path):
                os.remove(cover_path)

        db.session.delete(book)
        db.session.commit()
        flash('Book deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting book: {e}', 'danger')

    return redirect(url_for('teacher.teacher_dashboard'))
    


@teacher_bp.route('/approve_borrow/<int:request_id>', methods=['POST'])
@teacher_required
def approve_borrow(request_id):
    borrow_request = BorrowHistory.query.get_or_404(request_id)
    book = borrow_request.book

    user = User.query.get(session['user_id'])
    teacher = user.teacher_profile
    teacher_classes = teacher.classes  # Get all classes assigned to the teacher

    # Check if the book belongs to any class that the teacher manages
    if book.class_id not in [class_.id for class_ in teacher_classes]:
        flash("You cannot approve requests for books outside your assigned classes.", 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    # Check if the book is already borrowed
    if book.borrowed_by_id:
        flash(f'Book "{book.title}" is already borrowed by someone else.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    # Safely access the student associated with the borrow request
    student = borrow_request.student
    if not student:
        flash("Student not found.", 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    # Mark the book as borrowed by the student and update borrow request status
    book.borrowed_by_id = student.id
    book.borrowed_date = datetime.utcnow()

    borrow_request.borrow_date = datetime.utcnow()
    borrow_request.status = f"Borrowed by {student.name}"

    # Commit the changes to the database
    db.session.commit()
    flash(f'Borrow request for "{book.title}" approved!', 'success')
    return redirect(url_for('teacher.teacher_dashboard'))


@teacher_bp.route('/reject_borrow/<int:request_id>', methods=['POST'])
@teacher_required
def reject_borrow(request_id):
    borrow_request = BorrowHistory.query.get_or_404(request_id)
    book = borrow_request.book

    user = User.query.get(session['user_id'])
    teacher = user.teacher_profile
    teacher_classes = teacher.classes  # Get all classes assigned to the teacher

    # Check if the book belongs to any class that the teacher manages
    if book.class_id not in [class_.id for class_ in teacher_classes]:
        flash("You cannot reject requests for books outside your assigned classes.", 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    # Update the borrow request status as rejected
    borrow_request.status = f"Rejected by {teacher.name}"

    # Commit the changes to the database
    db.session.commit()

    flash(f'Borrow request for "{book.title}" has been rejected.', 'success')
    return redirect(url_for('teacher.teacher_dashboard'))


@teacher_bp.route('/return_book/<int:borrow_id>', methods=['POST'])
@teacher_required
def return_book(borrow_id):
    borrow_record = BorrowHistory.query.get_or_404(borrow_id)
    book = borrow_record.book

    user = User.query.get(session['user_id'])
    teacher = user.teacher_profile
    teacher_class = teacher.classes[0]

    if book.class_id != teacher_class.id:
        flash("You cannot return books outside your class.", 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    book.borrowed_by_id = None
    borrow_record.return_date = datetime.utcnow()
    borrow_record.status = f"Returned by {borrow_record.student.name}"

    db.session.commit()

    flash(f'Book "{book.title}" has been marked as returned.', "success")
    return redirect(url_for('teacher.teacher_dashboard'))



@teacher_bp.route('/approve_donation/<int:donation_id>', methods=['GET', 'POST'])
@teacher_required
def approve_donation(donation_id):
    donation_request = DonationRequest.query.get_or_404(donation_id)

    user = User.query.get(session['user_id'])
    teacher = user.teacher_profile
    teacher_class = teacher.classes[0]

    if donation_request.class_id != teacher_class.id:
        flash("You cannot approve donations outside your class.", 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    if request.method == 'POST':
        # Fetch data from form or Open Library API if available
        title = donation_request.title
        series = donation_request.series
        author = donation_request.author
        isbn = donation_request.isbn
        cover_url = None
        cover_filename = None
        if isbn:
            isbn_clean = isbn.replace('-', '').strip()
            openlibrary_url = f'https://openlibrary.org/api/books?bibkeys=ISBN%3A{isbn_clean}&jscmd=details&format=json'
            try:
                response = requests.get(openlibrary_url)
                if response.status_code == 200:
                    data = response.json()
                    book_key = f'ISBN:{isbn_clean}'
                    if book_key in data:
                        book_data = data[book_key]
                        details = book_data.get('details', {})
                        title = details.get('title', title)
                        # Get authors
                        authors_list = details.get('authors', [])
                        if authors_list:
                            author_names = []
                            for author_entry in authors_list:
                                author_name = author_entry.get('name', '')
                                if author_name:
                                    author_names.append(author_name)
                            author = ', '.join(author_names) if author_names else author
                        # Get cover
                        covers = details.get('covers', [])
                        if covers:
                            cover_id = covers[0]
                            cover_url = f'https://covers.openlibrary.org/b/id/{cover_id}-M.jpg'
                        else:
                            # Try to get thumbnail_url if cover is not available in details
                            cover_url = book_data.get('thumbnail_url', None)
                    else:
                        flash('ISBN not found in Open Library.', 'warning')
                else:
                    flash('Error fetching data from Open Library.', 'danger')
            except Exception as e:
                #flash(e)
                flash('Error fetching data from Open Library. except', 'danger')
        # Handle file upload
        file = request.files.get('cover_image')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = f"{datetime.utcnow().timestamp()}_{filename}"
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(upload_path)
            cover_filename = filename

        # Approve donation and create the book
        new_book = Book(
            title=title,
            series=series,
            author=author,
            isbn=isbn,
            cover_url=cover_url,
            cover_filename=cover_filename,
            donated_by_id=donation_request.student_id,
            class_id=donation_request.class_id
        )
        db.session.add(new_book)
        donation_request.status = "Approved"
        db.session.commit()

        flash(f'Donation of "{title}" has been approved and added to the inventory.', 'success')
        return redirect(url_for('teacher.teacher_dashboard'))

    return render_template('approve_donation.html', donation_request=donation_request)

@teacher_bp.route('/reject_donation/<int:donation_id>', methods=['POST'])
@teacher_required
def reject_donation(donation_id):
    donation_request = DonationRequest.query.get_or_404(donation_id)

    user = User.query.get(session['user_id'])
    teacher = user.teacher_profile
    teacher_class = teacher.classes[0]

    if donation_request.class_id != teacher_class.id:
        flash("You cannot reject donations outside your class.", 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    donation_request.status = "Rejected"

    db.session.commit()

    flash(f'Donation of "{donation_request.title}" has been rejected.', 'success')
    return redirect(url_for('teacher.teacher_dashboard'))

@teacher_bp.route('/teacher/book_details/<int:book_id>')
@teacher_required
def book_details(book_id):
    book = Book.query.get_or_404(book_id)

    user = User.query.get(session['user_id'])
    teacher = user.teacher_profile
    teacher_class = teacher.classes[0]

    if book.class_id != teacher_class.id:
        flash("You cannot view details of books outside your class.", 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    borrow_histories = BorrowHistory.query.filter_by(book_id=book.id).order_by(BorrowHistory.borrow_date.desc()).all()

    # Render the teacher-specific template
    return render_template('book_details_teacher.html', book=book, borrow_histories=borrow_histories)

@teacher_bp.route('/student_history/<int:student_id>')
@teacher_required
def student_history(student_id):
    student = Student.query.get_or_404(student_id)

    user = User.query.get(session['user_id'])
    teacher = user.teacher_profile
    teacher_class = teacher.classes[0]

    if student not in teacher_class.students:
        flash("You cannot view history of students outside your class.", 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    borrow_history = BorrowHistory.query.filter_by(student_id=student.id).order_by(BorrowHistory.id.desc()).all()
    donation_requests = DonationRequest.query.filter_by(student_id=student.id).order_by(DonationRequest.id.desc()).all()

    return render_template('student_history.html', student=student, borrow_history=borrow_history, donation_requests=donation_requests)

@teacher_bp.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
@teacher_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    user = User.query.get(session['user_id'])
    teacher = user.teacher_profile
    teacher_class = teacher.classes[0]

    if book.class_id != teacher_class.id:
        flash("You cannot edit books outside your class.", 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    if request.method == 'POST':
        # Update book details from form
        book.title = request.form['title']
        book.series = request.form['series']
        book.author = request.form['author']
        book.isbn = request.form['isbn']

        # Handle file upload for cover image
        file = request.files.get('cover_image')
        if file and allowed_file(file.filename):
            # Remove old cover image if exists
            if book.cover_filename:
                old_cover_path = os.path.join(current_app.config['UPLOAD_FOLDER'], book.cover_filename)
                if os.path.exists(old_cover_path):
                    os.remove(old_cover_path)

            # Save new cover image
            filename = secure_filename(file.filename)
            filename = f"{datetime.utcnow().timestamp()}_{filename}"
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(upload_path)
            book.cover_filename = filename

        db.session.commit()
        flash(f'Book "{book.title}" has been updated successfully!', 'success')
        return redirect(url_for('teacher.teacher_dashboard'))

    return render_template('edit_book.html', book=book)


@teacher_bp.route('/add_book', methods=['GET', 'POST'])
@teacher_required
def add_book():
    user = User.query.get(session['user_id'])
    teacher = user.teacher_profile

    # Fetch the classes the teacher is responsible for
    teacher_classes = teacher.classes

    if request.method == 'POST':
        title = request.form.get('title')
        series = request.form.get('series')
        author = request.form.get('author')
        isbn = request.form.get('isbn')
        class_id = request.form.get('class_id')

        # Check if the class belongs to the teacher
        if not any(class_.id == int(class_id) for class_ in teacher_classes):
            flash("You cannot add books to a class that you don't manage.", 'danger')
            return redirect(url_for('teacher.teacher_dashboard'))

        # Create and add a new book to the database
        new_book = Book(
            title=title,
            series=series,
            author=author,
            isbn=isbn,
            class_id=class_id
        )
        db.session.add(new_book)
        db.session.commit()

        flash(f'Book "{title}" has been added successfully!', 'success')
        return redirect(url_for('teacher.teacher_dashboard'))

    return render_template('add_book.html', classes=teacher_classes)
