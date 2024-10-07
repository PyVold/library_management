# student.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, User, Student, Class, Book, BorrowHistory, DonationRequest
from functools import wraps
from datetime import datetime

student_bp = Blueprint('student', __name__, template_folder='templates')

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'student':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@student_bp.route('/')
@student_required
def index():
    user = User.query.get(session['user_id'])
    student = user.student_profile
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('auth.login'))

    student_class = student.classes[0]

    # Get books from the student's class
    books = Book.query.filter_by(class_id=student_class.id).all()

    # Borrow history for the student
    borrow_history = BorrowHistory.query.filter_by(student_id=student.id).order_by(BorrowHistory.id.desc()).filter(~BorrowHistory.status.contains('Rejected')).all()

    # Donation requests made by the student
    donation_requests = DonationRequest.query.filter_by(student_id=student.id).order_by(DonationRequest.id.desc()).all()

    # Get IDs of books the student has requested to borrow or currently borrowed and not returned
    requested_book_ids = set()
    
    # Books with pending borrow requests (exclude rejected requests)
    pending_requests = BorrowHistory.query.filter(
        BorrowHistory.student_id == student.id,
        BorrowHistory.borrow_date == None,
        ~BorrowHistory.status.contains('Rejected')
    ).all()
    requested_book_ids.update([request.book_id for request in pending_requests])

    # Books currently borrowed and not returned
    active_borrows = BorrowHistory.query.filter(
        BorrowHistory.student_id == student.id,
        BorrowHistory.return_date == None,
        BorrowHistory.borrow_date != None
    ).all()
    requested_book_ids.update([borrow.book_id for borrow in active_borrows])

    # Create a dictionary to map book IDs to borrow request IDs for borrowed books
    borrowed_book_ids = {borrow.book_id: borrow.id for borrow in active_borrows}
    #print(borrowed_book_ids)

    # Calculate total active requests and borrows
    total_active = len(pending_requests) + len(active_borrows)

    # Pass all variables to the template
    return render_template(
        'student_index.html',
        books=books,
        borrow_history=borrow_history,
        donation_requests=donation_requests,
        student_class=student_class,
        requested_book_ids=requested_book_ids,  # Pending borrow request IDs
        borrowed_book_ids=borrowed_book_ids,    # Borrowed book IDs
        pending_requests=pending_requests,      # Pass pending requests to match requests with books
        total_active=total_active
    )


@student_bp.route('/request_borrow/<int:book_id>', methods=['POST'])
@student_required
def request_borrow(book_id):
    user = User.query.get(session['user_id'])
    student = user.student_profile

    # Check if the student has reached the limit of 2 active borrow requests or borrowed books
    pending_requests_count = BorrowHistory.query.filter(
        BorrowHistory.student_id == student.id,
        BorrowHistory.borrow_date == None,
        ~BorrowHistory.status.contains('Rejected')
    ).count()
    active_borrows_count = BorrowHistory.query.filter(
        BorrowHistory.student_id == student.id,
        BorrowHistory.return_date == None,
        BorrowHistory.borrow_date != None
    ).count()
    total_active = pending_requests_count + active_borrows_count

    if total_active >= 2:
        flash("You cannot have more than 2 active borrow requests or borrowed books at a time.", 'danger')
        return redirect(url_for('student.index'))

    book = Book.query.get_or_404(book_id)

    # Check if the book belongs to the student's class
    if book.class_id != student.classes[0].id:
        flash("You cannot request books from another class.", 'danger')
        return redirect(url_for('student.index'))

    # Check if the book is already borrowed
    if book.borrowed_by_id:
        flash(f'The book "{book.title}" is already borrowed by someone else.', 'danger')
        return redirect(url_for('student.index'))

    # Check if the student has an active request or borrow for this book
    existing_request = BorrowHistory.query.filter(
        BorrowHistory.student_id == student.id,
        BorrowHistory.book_id == book_id,
        BorrowHistory.return_date == None,
        ~BorrowHistory.status.contains('Rejected')
    ).first()
    if existing_request:
        flash(f'You have already requested or borrowed "{book.title}".', 'danger')
        return redirect(url_for('student.index'))

    # Create a new borrow request
    borrow_request = BorrowHistory(
        book_id=book.id,
        student_id=student.id,
        borrow_date=None,
        status="Pending approval"
    )
    db.session.add(borrow_request)
    db.session.commit()

    flash(f'Request to borrow "{book.title}" has been sent successfully!', 'success')
    return redirect(url_for('student.index'))

@student_bp.route('/cancel_request/<int:request_id>', methods=['POST'])
@student_required
def cancel_request(request_id):
    borrow_request = BorrowHistory.query.get_or_404(request_id)
    user = User.query.get(session['user_id'])
    student = user.student_profile

    if borrow_request.student_id != student.id:
        flash("You cannot cancel a request you didn't make.", 'danger')
        return redirect(url_for('student.index'))

    if borrow_request.borrow_date:
        flash("You cannot cancel a request that has already been approved.", 'danger')
        return redirect(url_for('student.index'))

    db.session.delete(borrow_request)
    db.session.commit()

    flash("Your borrow request has been canceled.", 'success')
    return redirect(url_for('student.index'))

@student_bp.route('/return_book/<int:borrow_id>', methods=['POST'])
@student_required
def return_book(borrow_id):
    borrow_record = BorrowHistory.query.get_or_404(borrow_id)
    book = borrow_record.book

    user = User.query.get(session['user_id'])
    student = user.student_profile

    if borrow_record.student_id != student.id:
        flash("You cannot return books borrowed by other students.", 'danger')
        return redirect(url_for('student.index'))

    if borrow_record.return_date:
        flash("This book has already been returned.", 'danger')
        return redirect(url_for('student.index'))

    book.borrowed_by_id = None
    borrow_record.return_date = datetime.utcnow()
    borrow_record.status = f"Returned by {student.name}"

    db.session.commit()

    flash(f'Book "{book.title}" has been returned successfully!', 'success')
    return redirect(url_for('student.index'))

@student_bp.route('/book_details/<int:book_id>')
@student_required
def book_details(book_id):
    book = Book.query.get_or_404(book_id)

    user = User.query.get(session['user_id'])
    student = user.student_profile
    if book.class_id != student.classes[0].id:
        flash("You cannot view details of books from another class.", 'danger')
        return redirect(url_for('student.index'))

    borrow_histories = BorrowHistory.query.filter_by(book_id=book.id).order_by(BorrowHistory.borrow_date.desc()).all()

    # Get IDs of books the student has requested or borrowed
    requested_book_ids = set()
    pending_requests = BorrowHistory.query.filter(
        BorrowHistory.student_id == student.id,
        BorrowHistory.borrow_date == None,
        ~BorrowHistory.status.contains('Rejected')
    ).all()
    requested_book_ids.update([request.book_id for request in pending_requests])
    active_borrows = BorrowHistory.query.filter(
        BorrowHistory.student_id == student.id,
        BorrowHistory.return_date == None,
        BorrowHistory.borrow_date != None
    ).all()
    requested_book_ids.update([borrow.book_id for borrow in active_borrows])

    total_active = len(pending_requests) + len(active_borrows)

    return render_template(
        'book_details.html',
        book=book,
        borrow_histories=borrow_histories,
        requested_book_ids=requested_book_ids,
        total_active=total_active
    )

@student_bp.route('/request_donate', methods=['GET', 'POST'])
@student_required
def request_donate():
    user = User.query.get(session['user_id'])
    student = user.student_profile

    if request.method == 'POST':
        isbn = request.form.get('isbn')
        title = request.form.get('title')
        series = request.form.get('series')
        author = request.form.get('author')

        # Create a new donation request
        new_request = DonationRequest(
            title=title,
            series=series,
            author=author,
            isbn=isbn,
            student_id=student.id,
            class_id=student.classes[0].id,
            status="Pending approval"
        )
        db.session.add(new_request)
        db.session.commit()

        flash('Your donation request has been sent successfully!', 'success')
        return redirect(url_for('student.index'))

    return render_template('request_donate.html')
    