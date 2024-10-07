from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime

db = SQLAlchemy()

# Many-to-Many relationship between students and classes
student_class = db.Table('student_class',
    Column('student_id', Integer, ForeignKey('student.id', ondelete='CASCADE')),
    Column('class_id', Integer, ForeignKey('class.id', ondelete='CASCADE'))
)

# Many-to-Many relationship between teachers and classes
teacher_class = db.Table('teacher_class',
    Column('teacher_id', Integer, ForeignKey('teacher.id', ondelete='CASCADE')),
    Column('class_id', Integer, ForeignKey('class.id', ondelete='CASCADE'))
)

class User(db.Model):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    username = Column(String(150), nullable=False, unique=True)
    password = Column(String(128), nullable=False)
    role = Column(String(50), nullable=False)  # 'student' or 'teacher'

    # One-to-One relationships
    student_profile = relationship('Student', back_populates='user', uselist=False)
    teacher_profile = relationship('Teacher', back_populates='user', uselist=False)

class Student(db.Model):
    __tablename__ = 'student'
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)

    # Relationships
    user = relationship('User', back_populates='student_profile')
    classes = relationship('Class', secondary=student_class, back_populates='students')
    borrow_histories = relationship('BorrowHistory', back_populates='student', cascade='all, delete', passive_deletes=True)
    donation_requests = relationship('DonationRequest', back_populates='student', cascade='all, delete', passive_deletes=True)

class Teacher(db.Model):
    __tablename__ = 'teacher'
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)

    # Relationships
    user = relationship('User', back_populates='teacher_profile')
    classes = relationship('Class', secondary=teacher_class, back_populates='teachers')

class Class(db.Model):
    __tablename__ = 'class'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)

    # Relationships
    students = relationship('Student', secondary=student_class, back_populates='classes')
    teachers = relationship('Teacher', secondary=teacher_class, back_populates='classes')
    books = relationship('Book', back_populates='class_', cascade='all, delete', passive_deletes=True)
    donation_requests = relationship('DonationRequest', back_populates='class_', cascade='all, delete', passive_deletes=True)

class Book(db.Model):
    __tablename__ = 'book'
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    series = Column(String(200))
    author = Column(String(200), nullable=False)
    isbn = Column(String(20))
    cover_url = Column(String(500))  # External URLs
    cover_filename = Column(String(500))  # Local filenames for uploaded images
    donated_by_id = Column(Integer, ForeignKey('student.id', ondelete='SET NULL'))
    class_id = Column(Integer, ForeignKey('class.id', ondelete='CASCADE'), nullable=False)
    borrowed_by_id = Column(Integer, ForeignKey('student.id', ondelete='SET NULL'))
    borrowed_date = Column(DateTime)

    # Relationships
    class_ = relationship('Class', back_populates='books')
    donor = relationship('Student', foreign_keys=[donated_by_id])
    borrower = relationship('Student', foreign_keys=[borrowed_by_id])
    borrow_histories = relationship('BorrowHistory', back_populates='book', cascade='all, delete', passive_deletes=True)

class BorrowHistory(db.Model):
    __tablename__ = 'borrow_history'
    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, ForeignKey('book.id', ondelete='CASCADE'), nullable=False)
    student_id = Column(Integer, ForeignKey('student.id', ondelete='CASCADE'), nullable=False)
    borrow_date = Column(DateTime)
    return_date = Column(DateTime)
    status = Column(String(50), nullable=False, default="Pending")

    # Relationships
    book = relationship('Book', back_populates='borrow_histories', passive_deletes=True)
    student = relationship('Student', back_populates='borrow_histories')

class DonationRequest(db.Model):
    __tablename__ = 'donation_request'
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    series = Column(String(200))
    author = Column(String(200), nullable=False)
    isbn = Column(String(20))
    student_id = Column(Integer, ForeignKey('student.id', ondelete='CASCADE'), nullable=False)
    class_id = Column(Integer, ForeignKey('class.id', ondelete='CASCADE'), nullable=False)
    status = Column(String(50), nullable=False, default="Pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    student = relationship('Student', back_populates='donation_requests')
    class_ = relationship('Class', back_populates='donation_requests')
