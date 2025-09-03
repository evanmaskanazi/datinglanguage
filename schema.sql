-- Table for Two Dating App Schema

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'admin', 'restaurant')),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- User profiles
CREATE TABLE user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    display_name VARCHAR(100) NOT NULL,
    age INTEGER CHECK (age >= 18 AND age <= 100),
    gender VARCHAR(20),
    bio TEXT,
    occupation VARCHAR(100),
    education VARCHAR(100),
    height INTEGER,
    profile_photo VARCHAR(500),
    verified_photo BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User preferences
CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    min_age INTEGER DEFAULT 18,
    max_age INTEGER DEFAULT 99,
    preferred_gender VARCHAR(20),
    max_distance INTEGER DEFAULT 50,
    interests TEXT[],
    values TEXT[],
    dealbreakers TEXT[],
    preferred_cuisines TEXT[],
    dietary_restrictions TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Restaurants
CREATE TABLE restaurants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    cuisine_type VARCHAR(100),
    address TEXT NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    phone VARCHAR(20),
    email VARCHAR(255),
    website VARCHAR(500),
    price_range INTEGER CHECK (price_range BETWEEN 1 AND 4),
    ambiance VARCHAR(50),
    rating DECIMAL(3, 2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Restaurant tables
CREATE TABLE restaurant_tables (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER REFERENCES restaurants(id) ON DELETE CASCADE,
    table_number VARCHAR(20) NOT NULL,
    capacity INTEGER DEFAULT 2,
    location VARCHAR(50), -- window, garden, corner, etc.
    is_available BOOLEAN DEFAULT TRUE,
    UNIQUE(restaurant_id, table_number)
);

-- Matches
CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    user1_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    user2_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    table_id INTEGER REFERENCES restaurant_tables(id),
    proposed_datetime TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined', 'expired', 'completed')),
    compatibility_score INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP,
    UNIQUE(user1_id, user2_id, proposed_datetime)
);

-- Reservations
CREATE TABLE reservations (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id),
    table_id INTEGER REFERENCES restaurant_tables(id),
    date_time TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'cancelled', 'completed', 'no_show')),
    confirmation_code VARCHAR(20) UNIQUE,
    special_requests TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Payments
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    reservation_id INTEGER REFERENCES reservations(id),
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'refunded')),
    stripe_payment_id VARCHAR(255),
    stripe_charge_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Date feedback
CREATE TABLE date_feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    reservation_id INTEGER REFERENCES reservations(id),
    match_user_id INTEGER REFERENCES users(id),
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    showed_up BOOLEAN,
    would_meet_again BOOLEAN,
    chemistry_level INTEGER CHECK (chemistry_level BETWEEN 1 AND 5),
    conversation_quality INTEGER CHECK (conversation_quality BETWEEN 1 AND 5),
    overall_experience INTEGER CHECK (overall_experience BETWEEN 1 AND 5),
    comments TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, reservation_id)
);

-- User blocks/reports
CREATE TABLE user_blocks (
    id SERIAL PRIMARY KEY,
    blocker_id INTEGER REFERENCES users(id),
    blocked_id INTEGER REFERENCES users(id),
    reason VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(blocker_id, blocked_id)
);

-- Notifications
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT,
    data JSONB,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit logs
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_matches_users ON matches(user1_id, user2_id);
CREATE INDEX idx_matches_status ON matches(status);
CREATE INDEX idx_reservations_datetime ON reservations(date_time);
CREATE INDEX idx_payments_user ON payments(user_id);
CREATE INDEX idx_feedback_reservation ON date_feedback(reservation_id);
CREATE INDEX idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at);
