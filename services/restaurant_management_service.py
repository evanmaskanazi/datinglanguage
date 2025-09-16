"""Restaurant management service for analytics and booking management"""
from datetime import datetime, timedelta, date
from flask import jsonify
from sqlalchemy import func, and_, or_
from models.restaurant_management import RestaurantAnalytics, RestaurantBooking, RestaurantSettings
from models.restaurant import Restaurant, RestaurantTable
from models.match import Match
from models.user import User

class RestaurantManagementService:
    def __init__(self, db, logger):
        self.db = db
        self.logger = logger

    def get_restaurant_stats(self, restaurant_id):
        """Get comprehensive restaurant statistics"""
        try:
            restaurant = Restaurant.query.get(restaurant_id)
            if not restaurant:
                return jsonify({'error': 'Restaurant not found'}), 404

            # Get date ranges
            today = date.today()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)

            # Total bookings
            total_bookings = RestaurantBooking.query.filter_by(restaurant_id=restaurant_id).count()
            
            # Confirmed bookings
            confirmed_bookings = RestaurantBooking.query.filter_by(
                restaurant_id=restaurant_id, status='confirmed'
            ).count()
            
            # Recent bookings (30 days)
            recent_bookings = RestaurantBooking.query.filter(
                RestaurantBooking.restaurant_id == restaurant_id,
                RestaurantBooking.created_at >= month_ago
            ).count()
            
            # Success rate
            success_rate = 0
            if total_bookings > 0:
                completed_bookings = RestaurantBooking.query.filter_by(
                    restaurant_id=restaurant_id, status='completed'
                ).count()
                success_rate = round((completed_bookings / total_bookings) * 100, 1)

            # Weekly stats
            weekly_stats = []
            for i in range(7):
                day = today - timedelta(days=i)
                day_bookings = RestaurantBooking.query.filter(
                    RestaurantBooking.restaurant_id == restaurant_id,
                    func.date(RestaurantBooking.created_at) == day
                ).count()
                weekly_stats.append({
                    'date': day.isoformat(),
                    'bookings': day_bookings
                })

            return jsonify({
                'total_requests': total_bookings,
                'confirmed_matches': confirmed_bookings,
                'recent_requests': recent_bookings,
                'success_rate': success_rate,
                'weekly_stats': weekly_stats,
                'restaurant_name': restaurant.name
            })

        except Exception as e:
            self.logger.error(f"Get restaurant stats error: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to get statistics'}), 500

    def get_match_requests(self, restaurant_id, date_filter=None):
        """Get match requests for restaurant"""
        try:
            restaurant = Restaurant.query.get(restaurant_id)
            if not restaurant:
                return jsonify({'error': 'Restaurant not found'}), 404

            query = RestaurantBooking.query.filter_by(restaurant_id=restaurant_id)

            # Apply date filter
            if date_filter == 'today':
                query = query.filter(func.date(RestaurantBooking.created_at) == date.today())
            elif date_filter == 'week':
                week_ago = date.today() - timedelta(days=7)
                query = query.filter(RestaurantBooking.created_at >= week_ago)

            bookings = query.order_by(RestaurantBooking.created_at.desc()).all()

            result = []
            for booking in bookings:
                user1 = User.query.get(booking.user1_id)
                user2 = User.query.get(booking.user2_id)
                
                result.append({
                    'id': booking.id,
                    'user1_email': user1.email if user1 else 'Unknown',
                    'user2_email': user2.email if user2 else 'Unknown',
                    'table_id': booking.table_id,
                    'status': booking.status,
                    'requested_datetime': booking.booking_datetime.isoformat() if booking.booking_datetime else None,
                    'created_at': booking.created_at.isoformat(),
                    'party_size': booking.party_size,
                    'special_requests': booking.special_requests
                })

            return jsonify(result)

        except Exception as e:
            self.logger.error(f"Get match requests error: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to get match requests'}), 500

    def update_booking_status(self, restaurant_id, booking_id, new_status):
        """Update booking status"""
        try:
            booking = RestaurantBooking.query.filter_by(
                id=booking_id, restaurant_id=restaurant_id
            ).first()
            
            if not booking:
                return jsonify({'error': 'Booking not found'}), 404

            booking.status = new_status
            booking.updated_at = datetime.utcnow()
            self.db.session.commit()

            return jsonify({
                'message': f'Booking status updated to {new_status}',
                'booking_id': booking_id
            })

        except Exception as e:
            self.logger.error(f"Update booking status error: {str(e)}", exc_info=True)
            self.db.session.rollback()
            return jsonify({'error': 'Failed to update booking'}), 500

    def get_restaurant_settings(self, restaurant_id):
        """Get restaurant settings"""
        try:
            restaurant = Restaurant.query.get(restaurant_id)
            if not restaurant:
                return jsonify({'error': 'Restaurant not found'}), 404

            settings = RestaurantSettings.query.filter_by(restaurant_id=restaurant_id).first()
            
            if not settings:
                # Create default settings
                settings = RestaurantSettings(restaurant_id=restaurant_id)
                self.db.session.add(settings)
                self.db.session.commit()

            return jsonify({
                'restaurant_name': restaurant.name,
                'cuisine_type': restaurant.cuisine_type,
                'address': restaurant.address,
                'rating': float(restaurant.rating) if restaurant.rating else 0.0,
                'price_range': restaurant.price_range,
                'notification_email': settings.notification_email,
                'auto_accept_bookings': settings.auto_accept_bookings,
                'max_advance_days': settings.max_advance_days,
                'min_advance_hours': settings.min_advance_hours,
                'special_instructions': settings.special_instructions
            })

        except Exception as e:
            self.logger.error(f"Get restaurant settings error: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to get settings'}), 500

    def update_restaurant_settings(self, restaurant_id, settings_data):
        """Update restaurant settings"""
        try:
            restaurant = Restaurant.query.get(restaurant_id)
            if not restaurant:
                return jsonify({'error': 'Restaurant not found'}), 404

            # Update restaurant basic info
            if 'restaurant_name' in settings_data:
                restaurant.name = settings_data['restaurant_name']
            if 'cuisine_type' in settings_data:
                restaurant.cuisine_type = settings_data['cuisine_type']
            if 'address' in settings_data:
                restaurant.address = settings_data['address']
            if 'price_range' in settings_data:
                restaurant.price_range = int(settings_data['price_range'])

            # Update or create settings
            settings = RestaurantSettings.query.filter_by(restaurant_id=restaurant_id).first()
            if not settings:
                settings = RestaurantSettings(restaurant_id=restaurant_id)
                self.db.session.add(settings)

            if 'notification_email' in settings_data:
                settings.notification_email = settings_data['notification_email']
            if 'auto_accept_bookings' in settings_data:
                settings.auto_accept_bookings = bool(settings_data['auto_accept_bookings'])
            if 'max_advance_days' in settings_data:
                settings.max_advance_days = int(settings_data['max_advance_days'])
            if 'min_advance_hours' in settings_data:
                settings.min_advance_hours = int(settings_data['min_advance_hours'])
            if 'special_instructions' in settings_data:
                settings.special_instructions = settings_data['special_instructions']

            settings.updated_at = datetime.utcnow()
            self.db.session.commit()

            return jsonify({'message': 'Settings updated successfully'})

        except Exception as e:
            self.logger.error(f"Update restaurant settings error: {str(e)}", exc_info=True)
            self.db.session.rollback()
            return jsonify({'error': 'Failed to update settings'}), 500

    def get_analytics_data(self, restaurant_id, period='week'):
        """Get detailed analytics data"""
        try:
            restaurant = Restaurant.query.get(restaurant_id)
            if not restaurant:
                return jsonify({'error': 'Restaurant not found'}), 404

            # Determine date range
            today = date.today()
            if period == 'week':
                start_date = today - timedelta(days=7)
            elif period == 'month':
                start_date = today - timedelta(days=30)
            elif period == 'year':
                start_date = today - timedelta(days=365)
            else:
                start_date = today - timedelta(days=7)

            # Get bookings data
            bookings_query = RestaurantBooking.query.filter(
                RestaurantBooking.restaurant_id == restaurant_id,
                RestaurantBooking.created_at >= start_date
            )

            # Group by date
            daily_stats = {}
            current_date = start_date
            while current_date <= today:
                day_bookings = bookings_query.filter(
                    func.date(RestaurantBooking.created_at) == current_date
                ).all()
                
                daily_stats[current_date.isoformat()] = {
                    'date': current_date.isoformat(),
                    'total_bookings': len(day_bookings),
                    'confirmed': len([b for b in day_bookings if b.status == 'confirmed']),
                    'completed': len([b for b in day_bookings if b.status == 'completed']),
                    'cancelled': len([b for b in day_bookings if b.status == 'cancelled'])
                }
                current_date += timedelta(days=1)

            return jsonify({
                'period': period,
                'daily_stats': list(daily_stats.values()),
                'summary': {
                    'total_period_bookings': bookings_query.count(),
                    'confirmed_rate': self._calculate_rate(bookings_query, 'confirmed'),
                    'completion_rate': self._calculate_rate(bookings_query, 'completed'),
                    'cancellation_rate': self._calculate_rate(bookings_query, 'cancelled')
                }
            })

        except Exception as e:
            self.logger.error(f"Get analytics data error: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to get analytics'}), 500

    def _calculate_rate(self, query, status):
        """Calculate percentage rate for given status"""
        total = query.count()
        if total == 0:
            return 0
        status_count = query.filter_by(status=status).count()
        return round((status_count / total) * 100, 1)

    def create_sample_booking(self, restaurant_id, user1_id, user2_id, datetime_str):
        """Create a sample booking for testing"""
        try:
            booking = RestaurantBooking(
                restaurant_id=restaurant_id,
                user1_id=user1_id,
                user2_id=user2_id,
                booking_datetime=datetime.fromisoformat(datetime_str),
                status='pending'
            )
            self.db.session.add(booking)
            self.db.session.commit()
            
            return jsonify({
                'message': 'Sample booking created',
                'booking_id': booking.id
            })
            
        except Exception as e:
            self.logger.error(f"Create sample booking error: {str(e)}", exc_info=True)
            self.db.session.rollback()
            return jsonify({'error': 'Failed to create booking'}), 500

    # Legacy methods for backward compatibility (updated to use new models)
    def register_restaurant(self, restaurant_data):
        """Register a new restaurant account (legacy method)"""
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
            from dating_backend import bcrypt
            restaurant = Restaurant(
                name=restaurant_data['name'],
                owner_email=restaurant_data['email'],
                owner_password_hash=bcrypt.generate_password_hash(restaurant_data['password']).decode('utf-8'),
                cuisine_type=restaurant_data['cuisine_type'],
                address=restaurant_data['address'],
                price_range=restaurant_data.get('price_range', 2),
                is_partner=True,
                is_active=True
            )
            
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
        """Authenticate restaurant account (legacy method)"""
        try:
            email = login_data.get('email')
            password = login_data.get('password')
            
            if not email or not password:
                return jsonify({'error': 'Email and password required'}), 400
            
            restaurant = Restaurant.query.filter_by(
                owner_email=email,
                is_partner=True
            ).first()
            
            if not restaurant:
                return jsonify({'error': 'Invalid credentials'}), 401
                
            from dating_backend import bcrypt
            if not bcrypt.check_password_hash(restaurant.owner_password_hash, password):
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
