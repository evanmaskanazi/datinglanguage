"""Restaurant management service for analytics and booking management"""
from datetime import datetime, timedelta, date
from flask import jsonify
from sqlalchemy import func, and_, or_
from models.restaurant_management import RestaurantAnalytics, RestaurantBooking, RestaurantSettings
from models.restaurant import Restaurant, RestaurantTable
from models.match import Match
from models.user import User

class RestaurantManagementService:
    def __init__(self, db, email_manager, logger):
        self.db = db
        self.email_manager = email_manager
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
    """Get match requests for restaurant with proper date filtering"""
    try:
        from datetime import datetime, timedelta
        from models.restaurant_management import RestaurantBooking
        from models.user import User
        
        query = RestaurantBooking.query.filter_by(restaurant_id=restaurant_id)
        
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if date_filter == 'today':
            # Show all bookings for today (past and future)
            tomorrow = today + timedelta(days=1)
            query = query.filter(
                RestaurantBooking.booking_datetime >= today,
                RestaurantBooking.booking_datetime < tomorrow
            )
        elif date_filter == 'week':
            # Calculate the full week (Monday to Sunday)
            days_since_monday = today.weekday()
            week_start = today - timedelta(days=days_since_monday)
            week_end = week_start + timedelta(days=7)
            
            query = query.filter(
                RestaurantBooking.booking_datetime >= week_start,
                RestaurantBooking.booking_datetime < week_end
            )
        # For 'all time' or no filter, don't add date constraints - show all past and future
        
        bookings = query.order_by(RestaurantBooking.booking_datetime.desc()).all()
        
        result = []
        for booking in bookings:
            user1 = User.query.get(booking.user1_id)
            user2 = User.query.get(booking.user2_id)
            
            result.append({
                'id': booking.id,
                'user1_email': user1.email if user1 else 'Unknown',
                'user2_email': user2.email if user2 else 'Unknown',
                'requested_datetime': booking.booking_datetime.isoformat() if booking.booking_datetime else None,
                'status': booking.status,
                'party_size': booking.party_size,
                'special_requests': booking.special_requests,
                'created_at': booking.created_at.isoformat() if booking.created_at else None
            })
        
        return jsonify(result)
        
    except Exception as e:
        self.logger.error(f"Get match requests error: {str(e)}")
        return jsonify({'error': 'Failed to get match requests'}), 500

    def update_booking_status(self, restaurant_id, booking_id, new_status):
        """Update booking status"""
        try:
            booking = RestaurantBooking.query.filter_by(
                id=booking_id, restaurant_id=restaurant_id
            ).first()
            
            if not booking:
                return jsonify({'error': 'Booking not found'}), 404

            old_status = booking.status
            booking.status = new_status
            booking.updated_at = datetime.utcnow()
            self.db.session.commit()

            # Send email notifications when status changes
            if new_status == 'confirmed' and old_status != 'confirmed':
                self._send_booking_confirmation_email(booking)
            elif new_status == 'cancelled':
                self._send_booking_cancellation_email(booking)

            return jsonify({
                'message': f'Booking status updated to {new_status}',
                'booking_id': booking_id
            })

        except Exception as e:
            self.logger.error(f"Update booking status error: {str(e)}", exc_info=True)
            self.db.session.rollback()
            return jsonify({'error': 'Failed to update booking'}), 500

    def _send_booking_confirmation_email(self, booking):
        """Send booking confirmation email to users"""
        try:
            user1 = User.query.get(booking.user1_id)
            user2 = User.query.get(booking.user2_id)
            restaurant = Restaurant.query.get(booking.restaurant_id)
            
            if user1 and user2 and restaurant:
                # Send to both users
                for user in [user1, user2]:
                    self.email_manager.send_booking_confirmation(user, booking, restaurant)
                    
        except Exception as e:
            self.logger.error(f"Failed to send booking confirmation email: {str(e)}")

    def _send_booking_cancellation_email(self, booking):
        """Send booking cancellation email to users"""
        try:
            user1 = User.query.get(booking.user1_id)
            user2 = User.query.get(booking.user2_id)
            restaurant = Restaurant.query.get(booking.restaurant_id)
            
            if user1 and user2 and restaurant:
                # Send to both users
                for user in [user1, user2]:
                    self.email_manager.send_booking_cancellation(user, booking, restaurant)
                    
        except Exception as e:
            self.logger.error(f"Failed to send booking cancellation email: {str(e)}")

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

    def get_comprehensive_analytics(self, restaurant_id, period='week'):
        """Get comprehensive analytics with charts data"""
        try:
            restaurant = Restaurant.query.get(restaurant_id)
            if not restaurant:
                return jsonify({'error': 'Restaurant not found'}), 404

            # Determine date range
            today = date.today()
            if period == 'week':
                start_date = today - timedelta(days=7)
                date_format = '%a'  # Day abbreviation
            elif period == 'month':
                start_date = today - timedelta(days=30)
                date_format = '%m/%d'  # Month/day
            else:  # year
                start_date = today - timedelta(days=365)
                date_format = '%b'  # Month abbreviation

            # Get bookings in period
            bookings = RestaurantBooking.query.filter(
                RestaurantBooking.restaurant_id == restaurant_id,
                RestaurantBooking.created_at >= start_date
            ).all()

            # Daily booking trends
            daily_stats = {}
            current_date = start_date
            while current_date <= today:
                day_bookings = [b for b in bookings if b.created_at.date() == current_date]
                daily_stats[current_date.strftime(date_format)] = {
                    'date': current_date.isoformat(),
                    'total': len(day_bookings),
                    'confirmed': len([b for b in day_bookings if b.status == 'confirmed']),
                    'completed': len([b for b in day_bookings if b.status == 'completed']),
                    'cancelled': len([b for b in day_bookings if b.status == 'cancelled'])
                }
                if period == 'week':
                    current_date += timedelta(days=1)
                elif period == 'month':
                    current_date += timedelta(days=1)
                else:  # year - group by month
                    current_date += timedelta(days=30)

            # Status distribution for pie chart
            status_counts = {
                'pending': len([b for b in bookings if b.status == 'pending']),
                'confirmed': len([b for b in bookings if b.status == 'confirmed']),
                'completed': len([b for b in bookings if b.status == 'completed']),
                'cancelled': len([b for b in bookings if b.status == 'cancelled'])
            }

            # Peak hours analysis
            hour_counts = {}
            for booking in bookings:
                if booking.booking_datetime:
                    hour = booking.booking_datetime.hour
                    if hour not in hour_counts:
                        hour_counts[hour] = 0
                    hour_counts[hour] += 1

            peak_hours = [{'hour': f'{h}:00', 'bookings': count} 
                         for h, count in sorted(hour_counts.items())]

            # Success metrics
            total_bookings = len(bookings)
            completed_bookings = status_counts['completed']
            success_rate = (completed_bookings / total_bookings * 100) if total_bookings > 0 else 0

            # Weekly vs Previous week comparison
            if period == 'week':
                prev_week_start = start_date - timedelta(days=7)
                prev_week_bookings = RestaurantBooking.query.filter(
                    RestaurantBooking.restaurant_id == restaurant_id,
                    RestaurantBooking.created_at >= prev_week_start,
                    RestaurantBooking.created_at < start_date
                ).count()
                
                current_week_bookings = len(bookings)
                week_change = ((current_week_bookings - prev_week_bookings) / prev_week_bookings * 100) if prev_week_bookings > 0 else 0
            else:
                week_change = 0

            return jsonify({
                'period': period,
                'summary': {
                    'total_bookings': total_bookings,
                    'completed_bookings': completed_bookings,
                    'success_rate': round(success_rate, 1),
                    'week_change': round(week_change, 1),
                    'average_daily': round(total_bookings / 7 if period == 'week' else total_bookings / 30, 1)
                },
                'charts': {
                    'daily_trends': list(daily_stats.values()),
                    'status_distribution': [
                        {'status': status, 'count': count, 'percentage': round(count/total_bookings*100, 1) if total_bookings > 0 else 0}
                        for status, count in status_counts.items() if count > 0
                    ],
                    'peak_hours': peak_hours
                },
                'insights': self._generate_insights(bookings, restaurant, period)
            })

        except Exception as e:
            self.logger.error(f"Get comprehensive analytics error: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to get analytics'}), 500

    def _generate_insights(self, bookings, restaurant, period):
        """Generate actionable insights from booking data"""
        insights = []
        
        if not bookings:
            return ["No booking data available for this period."]

        # Success rate insight
        completed = len([b for b in bookings if b.status == 'completed'])
        total = len(bookings)
        success_rate = (completed / total * 100) if total > 0 else 0
        
        if success_rate > 80:
            insights.append(f"Excellent! {success_rate:.1f}% of your bookings are completed successfully.")
        elif success_rate > 60:
            insights.append(f"Good performance with {success_rate:.1f}% completion rate. Consider improving customer experience.")
        else:
            insights.append(f"Completion rate of {success_rate:.1f}% could be improved. Review cancellation reasons.")

        # Peak time insight
        hours = {}
        for booking in bookings:
            if booking.booking_datetime:
                hour = booking.booking_datetime.hour
                hours[hour] = hours.get(hour, 0) + 1
        
        if hours:
            peak_hour = max(hours.items(), key=lambda x: x[1])[0]
            peak_period = "evening" if peak_hour >= 18 else "afternoon" if peak_hour >= 12 else "morning"
            insights.append(f"Most popular booking time is {peak_hour}:00 ({peak_period}). Consider special offers during slower periods.")

        # Trend insight
        if len(bookings) > 5:
            insights.append("You're gaining traction! Keep up the excellent service to attract more couples.")
        elif len(bookings) > 0:
            insights.append("You're getting started with date bookings. Consider updating your restaurant profile to attract more couples.")

        return insights

    def get_customer_demographics(self, restaurant_id):
        """Get customer demographic analysis"""
        try:
            bookings = RestaurantBooking.query.filter_by(restaurant_id=restaurant_id).all()
            
            # Get user data for demographics
            user_ids = set()
            for booking in bookings:
                user_ids.add(booking.user1_id)
                user_ids.add(booking.user2_id)
            
            users = User.query.filter(User.id.in_(user_ids)).all()
            
            # Analyze demographics (simplified - you'd need age/location data in user profiles)
            demographics = {
                'total_unique_customers': len(user_ids),
                'repeat_customers': self._count_repeat_customers(bookings),
                'booking_frequency': {
                    'once': 0,
                    'few_times': 0,
                    'regular': 0
                },
                'popular_days': self._analyze_popular_days(bookings),
                'average_party_size': sum(b.party_size for b in bookings) / len(bookings) if bookings else 2
            }
            
            return jsonify(demographics)
            
        except Exception as e:
            self.logger.error(f"Get demographics error: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to get demographics'}), 500

    def _count_repeat_customers(self, bookings):
        """Count how many customers have booked multiple times"""
        user_counts = {}
        for booking in bookings:
            user_counts[booking.user1_id] = user_counts.get(booking.user1_id, 0) + 1
            user_counts[booking.user2_id] = user_counts.get(booking.user2_id, 0) + 1
        
        repeat_customers = sum(1 for count in user_counts.values() if count > 1)
        return repeat_customers

    def _analyze_popular_days(self, bookings):
        """Analyze which days of the week are most popular"""
        day_counts = {}
        for booking in bookings:
            if booking.booking_datetime:
                day_name = booking.booking_datetime.strftime('%A')
                day_counts[day_name] = day_counts.get(day_name, 0) + 1
        
        return sorted(day_counts.items(), key=lambda x: x[1], reverse=True)

    def get_revenue_analytics(self, restaurant_id, period='month'):
        """Get revenue analytics (simplified - would need integration with POS system)"""
        try:
            restaurant = Restaurant.query.get(restaurant_id)
            if not restaurant:
                return jsonify({'error': 'Restaurant not found'}), 404

            # For demonstration, we'll estimate revenue based on bookings and price range
            price_multipliers = {1: 25, 2: 45, 3: 75, 4: 120}  # Average per person
            avg_per_person = price_multipliers.get(restaurant.price_range, 50)

            if period == 'week':
                start_date = date.today() - timedelta(days=7)
            elif period == 'month':
                start_date = date.today() - timedelta(days=30)
            else:
                start_date = date.today() - timedelta(days=365)

            bookings = RestaurantBooking.query.filter(
                RestaurantBooking.restaurant_id == restaurant_id,
                RestaurantBooking.status == 'completed',
                RestaurantBooking.created_at >= start_date
            ).all()

            # Calculate estimated revenue
            total_revenue = sum(booking.party_size * avg_per_person for booking in bookings)
            total_bookings = len(bookings)
            avg_revenue_per_booking = total_revenue / total_bookings if total_bookings > 0 else 0

            return jsonify({
                'period': period,
                'total_estimated_revenue': total_revenue,
                'total_bookings': total_bookings,
                'average_per_booking': round(avg_revenue_per_booking, 2),
                'average_per_person': avg_per_person,
                'note': 'Revenue estimates based on your price range and completed bookings'
            })

        except Exception as e:
            self.logger.error(f"Get revenue analytics error: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to get revenue analytics'}), 500

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
