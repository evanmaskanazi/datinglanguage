"""
Service for handling user and restaurant following functionality
"""
from flask import jsonify
from sqlalchemy import and_
from datetime import datetime, timedelta
from models.user import User
from models.restaurant import Restaurant
from dating_backend import db, bcrypt

class FollowingService:
    def __init__(self, db_session, cache_manager, logger):
        self.db = db_session
        self.cache = cache_manager
        self.logger = logger
    
    def follow_user(self, follower_id, following_id):
        """Follow another user"""
        try:
            if follower_id == following_id:
                return jsonify({'error': 'Cannot follow yourself'}), 400
            
            follower = User.query.get(follower_id)
            following = User.query.get(following_id)
            
            if not follower or not following:
                return jsonify({'error': 'User not found'}), 404
            
            if follower.is_following_user(following):
                return jsonify({'error': 'Already following this user'}), 400
            
            follower.follow_user(following)
            self.db.session.commit()
            
            # Clear cache
            self.cache.delete(f"user_following_{follower_id}")
            self.cache.delete(f"user_followers_{following_id}")
            
            self.logger.info(f"User {follower_id} followed user {following_id}")
            return jsonify({'message': f'Now following {following.email}'}), 201
            
        except Exception as e:
            self.logger.error(f"Follow user error: {str(e)}")
            self.db.session.rollback()
            return jsonify({'error': 'Failed to follow user'}), 500
    
    def unfollow_user(self, follower_id, following_id):
        """Unfollow a user"""
        try:
            follower = User.query.get(follower_id)
            following = User.query.get(following_id)
            
            if not follower or not following:
                return jsonify({'error': 'User not found'}), 404
            
            if not follower.is_following_user(following):
                return jsonify({'error': 'Not following this user'}), 400
            
            follower.unfollow_user(following)
            self.db.session.commit()
            
            # Clear cache
            self.cache.delete(f"user_following_{follower_id}")
            self.cache.delete(f"user_followers_{following_id}")
            
            return jsonify({'message': f'Unfollowed {following.email}'}), 200
            
        except Exception as e:
            self.logger.error(f"Unfollow user error: {str(e)}")
            self.db.session.rollback()
            return jsonify({'error': 'Failed to unfollow user'}), 500
    
    def follow_restaurant(self, user_id, restaurant_id):
        """Follow a restaurant"""
        try:
            user = User.query.get(user_id)
            
            # Handle both internal and API restaurants
            if str(restaurant_id).startswith('api_'):
                # For API restaurants, we might need to create a placeholder
                restaurant = Restaurant.query.filter_by(external_id=restaurant_id[4:]).first()
                if not restaurant:
                    return jsonify({'error': 'Restaurant not found'}), 404
            else:
                restaurant = Restaurant.query.get(int(restaurant_id))
            
            if not user or not restaurant:
                return jsonify({'error': 'User or restaurant not found'}), 404
            
            if user.is_following_restaurant(restaurant):
                return jsonify({'error': 'Already following this restaurant'}), 400
            
            user.follow_restaurant(restaurant)
            self.db.session.commit()
            
            # Clear cache
            self.cache.delete(f"user_following_restaurants_{user_id}")
            self.cache.delete(f"restaurant_followers_{restaurant.id}")
            
            self.logger.info(f"User {user_id} followed restaurant {restaurant.id}")
            return jsonify({'message': f'Now following {restaurant.name}'}), 201
            
        except Exception as e:
            self.logger.error(f"Follow restaurant error: {str(e)}")
            self.db.session.rollback()
            return jsonify({'error': 'Failed to follow restaurant'}), 500
    
    def get_user_following(self, user_id):
        """Get list of users that a user is following"""
        try:
            cache_key = f"user_following_{user_id}"
            cached = self.cache.get(cache_key)
            if cached:
                return jsonify(cached)
            
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            following = [{'id': u.id, 'email': u.email} for u in user.following]
            
            self.cache.set(cache_key, following, timeout=300)
            return jsonify(following)
            
        except Exception as e:
            self.logger.error(f"Get following error: {str(e)}")
            return jsonify({'error': 'Failed to get following list'}), 500
    
    def get_followed_restaurants(self, user_id):
        """Get restaurants that a user follows"""
        try:
            cache_key = f"user_following_restaurants_{user_id}"
            cached = self.cache.get(cache_key)
            if cached:
                return jsonify(cached)
            
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            restaurants = [{
                'id': r.id,
                'name': r.name,
                'cuisine_type': r.cuisine_type,
                'address': r.address
            } for r in user.followed_restaurants]
            
            self.cache.set(cache_key, restaurants, timeout=300)
            return jsonify(restaurants)
            
        except Exception as e:
            self.logger.error(f"Get followed restaurants error: {str(e)}")
            return jsonify({'error': 'Failed to get followed restaurants'}), 500
