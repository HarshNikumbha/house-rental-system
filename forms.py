from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, FloatField, SelectField, FileField, MultipleFileField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange
from flask_wtf.file import FileAllowed, FileRequired

class RegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(2, 120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(6, 128)])
    confirm = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    is_owner = BooleanField('Register as Owner?')
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class PropertyForm(FlaskForm):
    title = StringField('Title', validators=[
        DataRequired(message='Property title is required'),
        Length(min=5, max=200, message='Title must be between 5 and 200 characters')
    ])
    
    description = TextAreaField('Description', validators=[
        DataRequired(message='Description is required'),
        Length(min=10, max=2000, message='Description must be between 10 and 2000 characters')
    ])
    
    location = StringField('Location', validators=[
        DataRequired(message='Location is required'),
        Length(min=5, max=150, message='Location must be between 5 and 150 characters')
    ])
    
    rent = FloatField('Monthly Rent (INR)', validators=[
        DataRequired(message='Rent amount is required'),
        NumberRange(min=100, max=10000000, message='Rent must be between ₹100 and ₹1,00,00,000')
    ])
    
    property_type = SelectField('Property Type', 
        choices=[
            ('', 'Select Property Type'),
            ('1BHK', '1BHK'),
            ('2BHK', '2BHK'),
            ('3BHK', '3BHK'), 
            ('Flat', 'Flat'),
            ('Villa', 'Villa'),
            ('Apartment', 'Apartment'),
            ('Studio', 'Studio'),
            ('Penthouse', 'Penthouse')
        ], 
        validators=[DataRequired(message='Please select a property type')]
    )
    
    # ✅ ADDED: Multiple image upload field
    images = MultipleFileField('Property Images', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp'], 
                   'Only images (JPG, JPEG, PNG, WEBP, GIF, BMP) are allowed!')
    ])
    
    submit = SubmitField('Save')

class MessageForm(FlaskForm):
    message_text = TextAreaField('Message', validators=[DataRequired(), Length(1,1000)])
    submit = SubmitField('Send Message')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(), 
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Reset Password')