import os
import sys
import webbrowser
from threading import Timer
from flask import Flask, render_template, redirect, url_for, flash, request, send_from_directory, jsonify
from config import Config
from models import db, User, Property, PropertyImage, Message as MessageModel, Favorite
from forms import RegisterForm, LoginForm, PropertyForm, MessageForm, ForgotPasswordForm, ResetPasswordForm
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, current_user, login_required, logout_user
from werkzeug.utils import secure_filename
from PIL import Image
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer 
from flask_mail import Mail, Message as MailMessage

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp', 'tiff', 'svg', 'ico', 'avif'}

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Flask-Mail
mail = Mail(app)

# Create serializer for password reset tokens
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------------------------------------------
# CONTEXT PROCESSORS (for base.html)
# -------------------------------------------------------

@app.context_processor
def inject_user():
    """Make current_user available to all templates"""
    return dict(current_user=current_user)

@app.context_processor
def utility_processor():
    """Make request endpoint available for active navigation"""
    def get_current_route():
        return request.endpoint
    return dict(get_current_route=get_current_route)

@app.context_processor
def inject_now():
    """Inject current datetime"""
    return {'now': datetime.utcnow()}

# -------------------------------------------------------
# ✅ Redirect '/' to login or home depending on user status
# -------------------------------------------------------
@app.route('/')
def home_redirect():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return redirect(url_for('login'))

# -------------------------------------------------------
# ✅ Home page (was your old index)
# -------------------------------------------------------
@app.route('/home')
@login_required
def index():
    q = request.args.get('q', '')
    min_rent = request.args.get('min_rent')
    max_rent = request.args.get('max_rent')
    ptype = request.args.get('type')
    sort = request.args.get('sort', 'newest')

    props = Property.query
    
    # Apply filters
    if q:
        props = props.filter(Property.title.ilike(f'%{q}%') | Property.location.ilike(f'%{q}%'))
    if min_rent:
        try:
            props = props.filter(Property.rent >= float(min_rent))
        except ValueError:
            pass
    if max_rent:
        try:
            props = props.filter(Property.rent <= float(max_rent))
        except ValueError:
            pass
    if ptype:
        props = props.filter(Property.property_type == ptype)
    
    # Apply sorting
    if sort == 'rent_low':
        props = props.order_by(Property.rent.asc())
    elif sort == 'rent_high':
        props = props.order_by(Property.rent.desc())
    elif sort == 'popular':
        props = props.order_by(Property.created_at.desc())
    else:  # newest first (default)
        props = props.order_by(Property.created_at.desc())

    # Get user's favorite property IDs - with error handling
    user_favorites = []
    if current_user.is_authenticated:
        try:
            # Try to access favorites, if the relationship exists
            if hasattr(current_user, 'favorites'):
                user_favorites = [f.property_id for f in current_user.favorites]
            else:
                # If favorites relationship doesn't exist, query the Favorite table directly
                user_favorites = [f.property_id for f in Favorite.query.filter_by(user_id=current_user.id).all()]
        except Exception as e:
            print(f"Error getting favorites: {e}")
            user_favorites = []
    
    props = props.limit(50).all()
    return render_template('index.html', properties=props, user_favorites=user_favorites)

# -------------------------------------------------------
# FAVORITES FUNCTIONALITY
# -------------------------------------------------------

@app.route('/favorites/toggle', methods=['POST'])
@login_required
def toggle_favorite():
    property_id = request.form.get('property_id')
    action = request.form.get('action')
    
    if not property_id:
        return jsonify({'success': False, 'error': 'Property ID required'})
    
    try:
        property_id = int(property_id)
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid property ID'})
    
    property = Property.query.get(property_id)
    if not property:
        return jsonify({'success': False, 'error': 'Property not found'})
    
    existing_favorite = Favorite.query.filter_by(
        user_id=current_user.id, 
        property_id=property_id
    ).first()
    
    if action == 'add' and not existing_favorite:
        favorite = Favorite(user_id=current_user.id, property_id=property_id)
        db.session.add(favorite)
        db.session.commit()
        return jsonify({'success': True, 'action': 'added'})
    
    elif action == 'remove' and existing_favorite:
        db.session.delete(existing_favorite)
        db.session.commit()
        return jsonify({'success': True, 'action': 'removed'})
    
    return jsonify({'success': True, 'action': 'no_change'})

@app.route('/favorites')
@login_required
def favorites():
    """Display user's favorite properties"""
    try:
        user_favorites = Favorite.query.filter_by(user_id=current_user.id).all()
        favorite_properties = [fav.property for fav in user_favorites]
        
        # Get user's favorite property IDs for the template
        user_favorite_ids = [f.property_id for f in user_favorites]
        
        return render_template('favorites.html', 
                             properties=favorite_properties, 
                             user_favorites=user_favorite_ids)
    except Exception as e:
        print(f"Error in favorites route: {e}")
        flash('Error loading favorites.', 'error')
        return redirect(url_for('index'))

# -------------------------------------------------------
# Profile Route
# -------------------------------------------------------

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    # Get user's favorite property IDs
    user_favorites = []
    try:
        user_favorites = [f.property_id for f in current_user.favorites]
    except Exception as e:
        print(f"Error getting favorites for profile: {e}")
        user_favorites = []
    
    # Get user's properties if they are an owner
    user_properties = []
    if current_user.is_owner:
        user_properties = Property.query.filter_by(owner_id=current_user.id).order_by(Property.created_at.desc()).all()
    
    return render_template('profile.html', 
                         user=current_user, 
                         user_favorites=user_favorites,
                         user_properties=user_properties)
                         
# -------------------------------------------------------
# Register
# -------------------------------------------------------
@app.route('/register', methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegisterForm()
    if form.validate_on_submit():
        existing = User.query.filter_by(email=form.email.data.lower()).first()
        if existing:
            flash('Email already registered. Please login.', 'warning')
            return redirect(url_for('login'))
        hashed = generate_password_hash(form.password.data)
        user = User(name=form.name.data, email=form.email.data.lower(), password=hashed, is_owner=form.is_owner.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

# -------------------------------------------------------
# Login
# -------------------------------------------------------
@app.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        flash('Invalid credentials.', 'danger')
    return render_template('login.html', form=form)

# -------------------------------------------------------
# Logout
# -------------------------------------------------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

# -------------------------------------------------------
# Owner Dashboard
# -------------------------------------------------------
@app.route('/owner/dashboard')
@login_required
def owner_dashboard():
    if not current_user.is_owner:
        flash('Access denied: not an owner account.', 'warning')
        return redirect(url_for('index'))
    properties = Property.query.filter_by(owner_id=current_user.id).order_by(Property.created_at.desc()).all()
    return render_template('owner_dashboard.html', properties=properties)

# -------------------------------------------------------
# Image Helper Functions
# -------------------------------------------------------
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(file_storage):
    if file_storage and allowed_file(file_storage.filename):
        filename = secure_filename(file_storage.filename)
        name, ext = os.path.splitext(filename)
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        final_name = f"{name}_{timestamp}{ext}"
        path = os.path.join(app.config['UPLOAD_FOLDER'], final_name)
        
        try:
            # Open and process the image
            image = Image.open(file_storage)
            # Convert to RGB if necessary (for PNG with transparency)
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            # Create thumbnail while maintaining aspect ratio
            image.thumbnail((1200, 800), Image.Resampling.LANCZOS)
            # Save the image
            image.save(path, 'JPEG', quality=85, optimize=True)
            print(f"Image saved successfully: {final_name}")
            return final_name
        except Exception as e:
            print(f"Error processing image {filename}: {e}")
            return None
    return None

# -------------------------------------------------------
# Add Property
# -------------------------------------------------------
@app.route('/property/add', methods=['GET','POST'])
@login_required
def add_property():
    if not current_user.is_owner:
        flash('Only owners can add properties.', 'warning')
        return redirect(url_for('index'))
    
    form = PropertyForm()
    print(f"DEBUG: Form submitted: {form.validate_on_submit()}")
    print(f"DEBUG: Form errors: {form.errors}")
    
    if form.validate_on_submit():
        print("DEBUG: Form validation passed")
        # Create the property first
        prop = Property(
            title=form.title.data,
            description=form.description.data,
            location=form.location.data,
            rent=form.rent.data,
            property_type=form.property_type.data,
            owner_id=current_user.id
        )
        db.session.add(prop)
        db.session.flush()  # Get the property ID without committing
        print(f"DEBUG: Property created with ID: {prop.id}")
        
        # Handle multiple images
        image_count = 0
        if 'images' in request.files:
            files = request.files.getlist('images')
            print(f"DEBUG: Number of files received: {len(files)}")
            for file in files:
                if file and file.filename != '':
                    print(f"DEBUG: Processing file: {file.filename}")
                    if allowed_file(file.filename):
                        filename = save_image(file)
                        if filename:
                            prop_image = PropertyImage(
                                filename=filename,
                                property_id=prop.id
                            )
                            db.session.add(prop_image)
                            image_count += 1
                            print(f"DEBUG: Saved image: {filename}")
                    else:
                        print(f"DEBUG: File type not allowed: {file.filename}")
        
        db.session.commit()
        print(f"DEBUG: Database committed successfully")
        
        if image_count > 0:
            flash(f'Property added successfully with {image_count} image(s).', 'success')
        else:
            flash('Property added successfully, but no images were uploaded.', 'info')
            
        return redirect(url_for('owner_dashboard'))
    else:
        print("DEBUG: Form validation failed")
        if request.method == 'POST':
            flash('Please fix the errors in the form.', 'danger')
    
    return render_template('add_property.html', form=form)

# -------------------------------------------------------
# Property Details
# -------------------------------------------------------
@app.route('/property/<int:prop_id>', methods=['GET','POST'])
def property_detail(prop_id):
    prop = Property.query.get_or_404(prop_id)
    form = MessageForm()
    
    # Get user's favorite status for this property
    is_favorite = False
    if current_user.is_authenticated:
        try:
            is_favorite = Favorite.query.filter_by(
                user_id=current_user.id, 
                property_id=prop_id
            ).first() is not None
        except Exception as e:
            print(f"Error checking favorite status: {e}")
            is_favorite = False
    
    if form.validate_on_submit() and current_user.is_authenticated:
        msg = MessageModel(
            tenant_id=current_user.id,
            owner_id=prop.owner_id,
            property_id=prop.id,
            message_text=form.message_text.data
        )
        db.session.add(msg)
        db.session.commit()
        flash('Message sent to owner.', 'success')
        return redirect(url_for('property_detail', prop_id=prop.id))
    
    messages = MessageModel.query.filter_by(property_id=prop.id).order_by(MessageModel.timestamp.desc()).all()
    
    return render_template('property_detail.html', 
                         property=prop, 
                         form=form, 
                         messages=messages,
                         is_favorite=is_favorite)

# -------------------------------------------------------
# Edit Property
# -------------------------------------------------------
@app.route('/property/<int:prop_id>/edit', methods=['GET','POST'])
@login_required
def edit_property(prop_id):
    prop = Property.query.get_or_404(prop_id)
    if prop.owner_id != current_user.id:
        flash('Not authorized to edit this property.', 'danger')
        return redirect(url_for('index'))
    
    form = PropertyForm(obj=prop)
    if form.validate_on_submit():
        prop.title = form.title.data
        prop.description = form.description.data
        prop.location = form.location.data
        prop.rent = form.rent.data
        prop.property_type = form.property_type.data
        
        # Check if user wants to replace existing images
        delete_existing = request.form.get('delete_existing_images') == 'true'
        new_image_count = 0
        
        # Handle image uploads
        if 'images' in request.files:
            files = request.files.getlist('images')
            has_new_images = any(file and file.filename != '' for file in files)
            
            if has_new_images:
                # If replacing images, delete old ones
                if delete_existing:
                    # Delete existing images from filesystem
                    for image in prop.images:
                        try:
                            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
                            if os.path.exists(image_path):
                                os.remove(image_path)
                                print(f"Deleted old image: {image.filename}")
                        except Exception as e:
                            print(f"Error deleting image {image.filename}: {e}")
                    
                    # Delete all PropertyImage records
                    PropertyImage.query.filter_by(property_id=prop.id).delete()
                    print(f"Deleted all existing image records for property {prop.id}")
                
                # Add new images
                for file in files:
                    if file and file.filename != '' and allowed_file(file.filename):
                        filename = save_image(file)
                        if filename:
                            prop_image = PropertyImage(
                                filename=filename,
                                property_id=prop.id
                            )
                            db.session.add(prop_image)
                            new_image_count += 1
                            print(f"Saved new image: {filename} for property {prop.id}")
                
                if new_image_count > 0:
                    flash(f'Updated property with {new_image_count} new image(s).', 'success')
                else:
                    flash('Property updated, but no valid images were uploaded.', 'warning')
                    
            elif delete_existing:
                # User checked replace but didn't upload new images - delete existing
                for image in prop.images:
                    try:
                        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
                        if os.path.exists(image_path):
                            os.remove(image_path)
                            print(f"Deleted image: {image.filename}")
                    except Exception as e:
                        print(f"Error deleting image {image.filename}: {e}")
                
                PropertyImage.query.filter_by(property_id=prop.id).delete()
                flash('All existing images have been removed.', 'info')
                print(f"Removed all images for property {prop.id}")
        
        # Single commit at the end for all changes
        db.session.commit()
        print(f"Successfully updated property {prop.id} with {new_image_count} new images")
        flash('Property updated successfully.', 'success')
        return redirect(url_for('owner_dashboard'))
    
    return render_template('edit_property.html', form=form, property=prop)

# -------------------------------------------------------
# Delete Property
# -------------------------------------------------------
@app.route('/property/<int:prop_id>/delete', methods=['POST'])
@login_required
def delete_property(prop_id):
    prop = Property.query.get_or_404(prop_id)
    if prop.owner_id != current_user.id:
        flash('Not authorized to delete this property.', 'danger')
        return redirect(url_for('index'))
    
    # Delete associated images from filesystem
    for image in prop.images:
        try:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            print(f"Error deleting image {image.filename}: {e}")
    
    # Delete associated favorites if Favorite table exists
    try:
        Favorite.query.filter_by(property_id=prop_id).delete()
    except Exception as e:
        print(f"Error deleting favorites: {e}")
    
    # The PropertyImage records will be automatically deleted due to cascade='all, delete-orphan'
    db.session.delete(prop)
    db.session.commit()
    flash('Property deleted.', 'info')
    return redirect(url_for('owner_dashboard'))

# -------------------------------------------------------
# Uploads + Search
# -------------------------------------------------------
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/search')
def search():
    q = request.args.get('q', '')
    min_rent = request.args.get('min_rent')
    max_rent = request.args.get('max_rent')
    ptype = request.args.get('type')
    sort = request.args.get('sort', 'relevance')

    props = Property.query
    if q:
        props = props.filter(Property.title.ilike(f'%{q}%') | Property.location.ilike(f'%{q}%'))
    if min_rent:
        try:
            props = props.filter(Property.rent >= float(min_rent))
        except Exception:
            pass
    if max_rent:
        try:
            props = props.filter(Property.rent <= float(max_rent))
        except Exception:
            pass
    if ptype:
        props = props.filter(Property.property_type == ptype)
    
    # Apply sorting
    if sort == 'rent_low':
        props = props.order_by(Property.rent.asc())
    elif sort == 'rent_high':
        props = props.order_by(Property.rent.desc())
    elif sort == 'newest':
        props = props.order_by(Property.created_at.desc())
    elif sort == 'oldest':
        props = props.order_by(Property.created_at.asc())
    else:  # relevance (default)
        props = props.order_by(Property.created_at.desc())

    # Get user's favorite property IDs with error handling
    user_favorites = []
    if current_user.is_authenticated:
        try:
            user_favorites = [f.property_id for f in Favorite.query.filter_by(user_id=current_user.id).all()]
        except Exception as e:
            print(f"Error getting favorites in search: {e}")
            user_favorites = []

    results = props.all()
    return render_template('search_results.html', properties=results, user_favorites=user_favorites)

# -------------------------------------------------------
# NEW ROUTES FOR ADDITIONAL PAGES
# -------------------------------------------------------

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# -------------------------------------------------------
# FORGOT PASSWORD ROUTES - FIXED
# -------------------------------------------------------

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():  # ✅ FIXED: validate_on_submit (not validate_onSubmit)
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        # For security, always show success message even if email doesn't exist
        flash('If an account with that email exists, a password reset link has been sent.', 'info')
        
        if user:
            # Generate reset token (valid for 1 hour)
            token = s.dumps(user.email, salt='password-reset-salt')
            
            # In development: show the reset link instead of emailing
            if app.config['DEBUG']:
                reset_url = url_for('reset_password', token=token, _external=True)
                flash(f'DEBUG: Reset URL: {reset_url}', 'info')
        
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html', form=form)

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    try:
        # Verify token (valid for 1 hour)
        email = s.loads(token, salt='password-reset-salt', max_age=3600)
    except:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('forgot_password'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=email).first()
        if user:
            # Update password
            user.password = generate_password_hash(form.password.data)
            db.session.commit()
            
            flash('Your password has been updated! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('User not found.', 'danger')
    
    return render_template('reset_password.html', form=form)

# -------------------------------------------------------
# ERROR HANDLERS
# -------------------------------------------------------

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

def open_browser():
    """Open web browser automatically when app starts"""
    import webbrowser
    webbrowser.open_new('http://127.0.0.1:5000/')

if __name__ == '__main__':
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("✅ Database recreated with favorites table")
    
    print("🚀 Starting House Rental Application...")
    print("📱 This app will run on all devices in your network")
    print("🌐 Access via: http://127.0.0.1:5000 (on this device)")
    print("🌐 Or use your IP address to access from other devices")
    print("⏹️  Press Ctrl+C to stop the server\n")
    
    # Open browser after 2 seconds
    import threading
    timer = threading.Timer(2, open_browser)
    timer.start()
    
    # Run on all network interfaces
    app.run(host='0.0.0.0', port=5000, debug=True)