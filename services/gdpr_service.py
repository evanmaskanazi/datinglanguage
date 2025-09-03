from flask import jsonify, send_file
import json
from io import BytesIO

class GDPRService:
    def __init__(self, db, logger):
        self.db = db
        self.logger = logger
    
    def export_user_data(self, user_id):
        """Export all user data for GDPR compliance"""
        try:
            # TODO: Gather all user data from various tables
            user_data = {
                'user_id': user_id,
                'export_date': datetime.utcnow().isoformat(),
                'data': {}  # Would include profile, preferences, matches, etc.
            }
            
            # Create JSON file
            data_file = BytesIO()
            data_file.write(json.dumps(user_data, indent=2).encode())
            data_file.seek(0)
            
            return send_file(
                data_file,
                as_attachment=True,
                download_name=f'user_data_{user_id}.json',
                mimetype='application/json'
            )
            
        except Exception as e:
            self.logger.error(f"Data export error: {str(e)}")
            return jsonify({'error': 'Failed to export data'}), 500
