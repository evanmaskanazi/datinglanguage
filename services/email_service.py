"""
Email service for sending notifications and communications
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

class EmailService:
    def __init__(self, app, logger):
        self.app = app
        self.logger = logger
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        self.smtp_username = os.environ.get('SMTP_USERNAME')
        self.smtp_password = os.environ.get('SMTP_PASSWORD')
        self.from_email = os.environ.get('FROM_EMAIL', 'noreply@tablefortwo.com')
    
    def send_email(self, to_email, subject, body, is_html=False):
        """Send email via SMTP"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # For now, just log the email instead of sending
            self.logger.info(f"Email would be sent to {to_email}: {subject}")
            return True
            
            # Uncomment when ready to send actual emails
            # server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            # server.starttls()
            # server.login(self.smtp_username, self.smtp_password)
            # text = msg.as_string()
            # server.sendmail(self.from_email, to_email, text)
            # server.quit()
            # return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def send_welcome_email(self, user):
        """Send welcome email to new user"""
        subject = "Welcome to Table for Two!"
        body = f"""
        Hi {user.username},
        
        Welcome to Table for Two! We're excited to help you find meaningful connections over great meals.
        
        Get started by:
        1. Completing your profile
        2. Setting your preferences
        3. Browsing local restaurants
        
        Happy dating!
        
        The Table for Two Team
        """
        return self.send_email(user.email, subject, body)
    
    def send_match_notification(self, user, match_user, restaurant):
        """Send match notification email"""
        subject = "You have a new match!"
        body = f"""
        Hi {user.username},
        
        Great news! You've been matched with {match_user.username} at {restaurant.name}.
        
        Log in to your account to view your match and plan your date.
        
        Happy dating!
        
        The Table for Two Team
        """
        return self.send_email(user.email, subject, body)
    
    def send_reservation_confirmation(self, user, reservation):
        """Send reservation confirmation email"""
        subject = "Your reservation is confirmed!"
        body = f"""
        Hi {user.username},
        
        Your reservation is confirmed for {reservation.date_time.strftime('%B %d, %Y at %I:%M %p')}.
        
        Restaurant: {reservation.restaurant.name}
        Address: {reservation.restaurant.address}
        
        We hope you have a wonderful date!
        
        The Table for Two Team
        """
        return self.send_email(user.email, subject, body)
