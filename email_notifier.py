"""
Email notification system for Flickr to Instagram automation.
Sends completion notifications to social media managers.
"""
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from config import Config


class EmailNotifier:
    """Handle email notifications for automation events."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def send_completion_notification(self, total_photos: int, album_name: str) -> bool:
        """Send album completion notification to the configured email address."""
        if not self.config.email_notifications_enabled:
            self.logger.info("📧 Email notifications not configured - skipping notification")
            return True
        
        try:
            # Create the email message
            msg = self._create_completion_email(total_photos, album_name)
            
            # Send the email
            success = self._send_email(msg)
            
            if success:
                self.logger.info(f"📧 Successfully sent album completion notification to {self.config.notification_email}")
                return True
            else:
                self.logger.error(f"❌ Failed to send album completion notification")
                return False
                
        except Exception as e:
            self.logger.error(f"💥 Email notification failed: {e}")
            return False
    
    def _create_completion_email(self, total_photos: int, album_name: str) -> MIMEMultipart:
        """Create the completion notification email."""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Album Complete: {album_name} ({total_photos} photos published)"
        msg['From'] = self.config.smtp_username
        msg['To'] = self.config.notification_email
        
        # Create both text and HTML versions
        text_content = self._create_text_content(total_photos, album_name)
        html_content = self._create_html_content(total_photos, album_name)
        
        # Create MIMEText objects
        text_part = MIMEText(text_content, 'plain')
        html_part = MIMEText(html_content, 'html')
        
        # Attach parts
        msg.attach(text_part)
        msg.attach(html_part)
        
        return msg
    
    def _create_text_content(self, total_photos: int, album_name: str) -> str:
        """Create plain text email content."""
        completion_date = datetime.now().strftime('%Y-%m-%d %H:%M UTC')
        
        return f"""Album Publishing Complete!

Album: {album_name}
Total Photos Published: {total_photos}
Completion Date: {completion_date}
Album URL: {self.config.album_url}

All photos from the "{album_name}" Flickr album have been successfully published to Instagram.

Next Steps:
1. Review the published posts on Instagram
2. Configure the next Flickr album for automation
3. Update the FLICKR_ALBUM_ID environment variable
4. Update the album name in config.py if needed

The automation system is ready for the next album configuration.

---
Flickr to Instagram Automation System
Generated automatically on {completion_date}
"""
    
    def _create_html_content(self, total_photos: int, album_name: str) -> str:
        """Create HTML email content."""
        completion_date = datetime.now().strftime('%Y-%m-%d %H:%M UTC')
        
        return f"""
        <html>
          <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #4CAF50; color: white; padding: 20px; border-radius: 8px; text-align: center;">
              <h1 style="margin: 0;">Album Publishing Complete!</h1>
            </div>
            
            <div style="padding: 20px; background-color: #f9f9f9; border-radius: 8px; margin: 20px 0;">
              <h2 style="color: #333;">Album Summary</h2>
              <table style="width: 100%; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid #ddd;">
                  <td style="padding: 8px; font-weight: bold;">Album Name:</td>
                  <td style="padding: 8px;">{album_name}</td>
                </tr>
                <tr style="border-bottom: 1px solid #ddd;">
                  <td style="padding: 8px; font-weight: bold;">Photos Published:</td>
                  <td style="padding: 8px;"><strong>{total_photos}</strong></td>
                </tr>
                <tr style="border-bottom: 1px solid #ddd;">
                  <td style="padding: 8px; font-weight: bold;">Completion Date:</td>
                  <td style="padding: 8px;">{completion_date}</td>
                </tr>
                <tr>
                  <td style="padding: 8px; font-weight: bold;">Album URL:</td>
                  <td style="padding: 8px;"><a href="{self.config.album_url}" style="color: #1976D2;">View on Flickr</a></td>
                </tr>
              </table>
            </div>
            
            <div style="padding: 20px; background-color: #e3f2fd; border-radius: 8px; border-left: 4px solid #1976D2;">
              <h3 style="color: #1976D2; margin-top: 0;">Next Steps</h3>
              <ol style="color: #333; line-height: 1.6;">
                <li><strong>Review Instagram Posts:</strong> Check that all photos were published correctly</li>
                <li><strong>Configure Next Album:</strong> Select the next Flickr album for automation</li>
                <li><strong>Update Configuration:</strong> Set the new <code>FLICKR_ALBUM_ID</code> environment variable</li>
                <li><strong>Update Album Name:</strong> Modify the album name in <code>config.py</code> if needed</li>
              </ol>
            </div>
            
            <div style="text-align: center; margin-top: 30px; padding: 20px; border-top: 1px solid #ddd;">
              <p style="color: #666; font-size: 14px;">
                Generated automatically by Flickr to Instagram Automation System<br>
                <em>{completion_date}</em>
              </p>
            </div>
          </body>
        </html>
        """
    
    def _send_email(self, msg: MIMEMultipart) -> bool:
        """Send email using SMTP."""
        try:
            # Create SMTP session
            server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
            server.starttls()  # Enable TLS encryption
            
            # Login to the SMTP server
            server.login(self.config.smtp_username, self.config.smtp_password)
            
            # Send email
            text = msg.as_string()
            server.sendmail(self.config.smtp_username, self.config.notification_email, text)
            server.quit()
            
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            self.logger.error(f"SMTP authentication failed: {e}")
            self.logger.error("Check SMTP_USERNAME and SMTP_PASSWORD credentials")
            return False
        except smtplib.SMTPConnectError as e:
            self.logger.error(f"SMTP connection failed: {e}")
            self.logger.error(f"Check SMTP_HOST ({self.config.smtp_host}) and SMTP_PORT ({self.config.smtp_port})")
            return False
        except smtplib.SMTPException as e:
            self.logger.error(f"SMTP error occurred: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending email: {e}")
            return False
    
    def test_email_configuration(self) -> bool:
        """Test email configuration by sending a test message."""
        if not self.config.email_notifications_enabled:
            self.logger.warning("Email notifications not configured")
            return False
        
        try:
            # Create a simple test message
            msg = MIMEText("This is a test message from the Flickr to Instagram automation system.")
            msg['Subject'] = "Email Configuration Test"
            msg['From'] = self.config.smtp_username
            msg['To'] = self.config.notification_email
            
            # Send the test email
            success = self._send_email(msg)
            
            if success:
                self.logger.info("Test email sent successfully")
                return True
            else:
                self.logger.error("Test email failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Test email failed: {e}")
            return False