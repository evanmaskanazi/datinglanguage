"""
Service for restaurant account management
"""
from flask import jsonify
from datetime import datetime, timedelta
from models.restaurant import Restaurant
from models.match import Match
from models.reservation import Reservation
from .. import db, bcrypt

class RestaurantManagementService:
    def __init__(self, db_session, logger):
        self.db = db_session
        self.logger = logger
    
    def register_restaurant(self, restaurant_data):
        """Register a new restaurant account"""
        try:
            required_fields = ['name', 'email', 'password', 'cuisine_type', 'address']
            for field in required_fields:
                if field not in restaurant_data:
                    return jsonify({'error': f'{field} is required'}), 400
            
            # Check if email already exists
            existing = Restaurant.query.filter_by(owner_email=restaurant_data['email']).first()
            if existing:
                return jsonify({'error': 'Email already registered'}), 400
            
            # Create new restaurant
            restaurant = Restaurant(
                name=restaurant_data['name'],
                owner_email=restaurant_data['email'],
                cuisine_type=restaurant_data['cuisine_type'],
                address=restaurant_data['address'],
                phone=restaurant_data.get('phone'),
                price_range=restaurant_data.get('price_range', 2),
                is_partner=True,  # Partner restaurants have accounts
                is_active=True
            )
            
            restaurant.set_password(restaurant_data['password'])
            
            self.db.session.add(restaurant)
            self.db.session.commit()
            
            self.logger.info(f"Restaurant registered: {restaurant.name}")
            return jsonify({
                'message': 'Restaurant registered successfully',
                'restaurant_id': restaurant.id
            }), 201
            
        except Exception as e:
            self.logger.error(f"Restaurant registration error: {str(e)}")
            self.db.session.rollback()
            return jsonify({'error': 'Registration failed'}), 500
    
    def restaurant_login(self, login_data):
        """Authenticate restaurant account"""
        try:
            email = login_data.get('email')
            password = login_data.get('password')
            
            if not email or not password:
                return jsonify({'error': 'Email and password required'}), 400
            
            restaurant = Restaurant.query.filter_by(
                owner_email=email,
                is_partner=True
            ).first()
            
            if not restaurant or not restaurant.check_password(password):
                return jsonify({'error': 'Invalid credentials'}), 401
            
            return jsonify({
                'success': True,
                'restaurant': {
                    'id': restaurant.id,
                    'name': restaurant.name,
                    'email': restaurant.owner_email,
                    'cuisine_type': restaurant.cuisine_type
                }
            }), 200
            
        except Exception as e:
            self.logger.error(f"Restaurant login error: {str(e)}")
            return jsonify({'error': 'Login failed'}), 500
    
    def get_match_requests(self, restaurant_id, date_filter=None):
        """Get match requests for this restaurant"""
        try:
            restaurant = Restaurant.query.get(restaurant_id)
            if not restaurant:
                return jsonify({'error': 'Restaurant not found'}), 404
            
            query = Match.query.filter_by(restaurant_id=str(restaurant_id))
            
            if date_filter:
                if date_filter == 'today':
                    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = start_date + timedelta(days=1)
                elif date_filter == 'week':
                    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = start_date + timedelta(days=7)
                else:
                    # Assume date_filter is a specific date
                    filter_date = datetime.strptime(date_filter, '%Y-%m-%d')
                    start_date = filter_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = start_date + timedelta(days=1)
                
                query = query.filter(
                    Match.proposed_datetime >= start_date,
                    Match.proposed_datetime < end_date
                )
            
            matches = query.order_by(Match.proposed_datetime).all()
            
            result = []
            for match in matches:
                # Get user information
                from ..models.user import User
                user1 = User.query.get(match.user1_id)
                user2 = User.query.get(match.user2_id)
                
                result.append({
                    'id': match.id,
                    'datetime': match.proposed_datetime.isoformat() if match.proposed_datetime else None,
                    'status': match.status.value if hasattr(match.status, 'value') else str(match.status),
                    'user1': {'id': user1.id, 'email': user1.email} if user1 else None,
                    'user2': {'id': user2.id, 'email': user2.email} if user2 else None,
                    'table_id': match.table_id,
                    'created_at': match.created_at.isoformat()
                })
            
            return jsonify(result)
            
        except Exception as e:
            self.logger.error(f"Get match requests error: {str(e)}")
            return jsonify({'error': 'Failed to get match requests'}), 500
    
    def get_restaurant_stats(self, restaurant_id):
        """Get statistics for restaurant dashboard"""
        try:
            restaurant = Restaurant.query.get(restaurant_id)
            if not restaurant:
                return jsonify({'error': 'Restaurant not found'}), 404
            
            # Get match statistics
            total_requests = Match.query.filter_by(restaurant_id=str(restaurant_id)).count()
            confirmed_matches = Match.query.filter_by(
                restaurant_id=str(restaurant_id),
                status='CONFIRMED'
            ).count()
            
            # Get recent activity (last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_requests = Match.query.filter(
                Match.restaurant_id == str(restaurant_id),
                Match.created_at >= thirty_days_ago
            ).count()
            
            # Follower count
            follower_count = restaurant.followers.count()
            
            return jsonify({
                'total_requests': total_requests,
                'confirmed_matches': confirmed_matches,
                'recent_requests': recent_requests,
                'followers': follower_count,
                'success_rate': round((confirmed_matches / total_requests * 100) if total_requests > 0 else 0, 1)
            })
            
        except Exception as e:
            self.logger.error(f"Get restaurant stats error: {str(e)}")
            return jsonify({'error': 'Failed to get statistics'}), 500
