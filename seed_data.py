from app import app
from models import db, User, Property
from werkzeug.security import generate_password_hash

with app.app_context():
    # clear tables (use carefully)
    db.drop_all()
    db.create_all()

    owner_pw = generate_password_hash('ownerpass')
    tenant_pw = generate_password_hash('tenantpass')

    owner = User(name='Alice Owner', email='owner@example.com', password=owner_pw, is_owner=True)
    tenant = User(name='Bob Tenant', email='tenant@example.com', password=tenant_pw, is_owner=False)
    db.session.add_all([owner, tenant])
    db.session.commit()

    p1 = Property(title='Cozy 1BHK near Mall', description='A compact 1BHK near the mall with good light.', location='Kondhwa, Pune', rent=8000, property_type='1BHK', owner_id=owner.id)
    p2 = Property(title='Spacious 2BHK with balcony', description='2BHK on the 3rd floor with balcony and parking.', location='Viman Nagar, Pune', rent=18000, property_type='2BHK', owner_id=owner.id)
    db.session.add_all([p1, p2])
    db.session.commit()

    print('Seed data created: owner@example.com / ownerpass, tenant@example.com / tenantpass')
