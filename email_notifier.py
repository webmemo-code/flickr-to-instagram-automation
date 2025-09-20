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
    
    def send_api_failure_alert(self,
                                blog_url: str,
                                error_details: dict,
                                account_name: str = "Unknown") -> bool:
        """
        Send email alert for WordPress API access failure.

        Args:
            blog_url: The blog URL that failed to load
            error_details: Dictionary containing error information
            account_name: Name of the account (primary/secondary)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.config.email_notifications_enabled:
            self.logger.debug("Email notifications not configured - skipping API failure alert")
            return True  # Return True to not block automation

        try:
            # Create the API failure email message
            msg = self._create_api_failure_email(blog_url, error_details, account_name)

            # Send the email
            success = self._send_email(msg)

            if success:
                self.logger.info(f"📧 API failure alert sent to {self.config.notification_email}")
                return True
            else:
                self.logger.error("❌ Failed to send API failure alert")
                return False

        except Exception as e:
            self.logger.error(f"💥 API failure email notification failed: {e}")
            return False

    def _create_api_failure_email(self,
                                 blog_url: str,
                                 error_details: dict,
                                 account_name: str) -> MIMEMultipart:
        """Create the API failure notification email."""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🚨 WordPress API Access Failure - {account_name} Account"
        msg['From'] = self.config.smtp_username
        msg['To'] = self.config.notification_email

        # Create both text and HTML versions
        text_content = self._create_api_failure_text_content(blog_url, error_details, account_name)
        html_content = self._create_api_failure_html_content(blog_url, error_details, account_name)

        # Create MIMEText objects
        text_part = MIMEText(text_content, 'plain')
        html_part = MIMEText(html_content, 'html')

        # Attach parts
        msg.attach(text_part)
        msg.attach(html_part)

        return msg

    def _create_api_failure_text_content(self,
                                        blog_url: str,
                                        error_details: dict,
                                        account_name: str) -> str:
        """Create plain text email content for API failure."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M UTC')

        # Extract error information
        http_status = error_details.get('http_status', 'Unknown')
        error_message = error_details.get('error_message', 'No specific error message')
        attempted_methods = error_details.get('attempted_methods', [])
        fallback_used = error_details.get('fallback_used', False)

        return f"""WordPress API Access Failure Alert

ACCOUNT: {account_name}
TIME: {timestamp}
BLOG URL: {blog_url}

ERROR DETAILS:
- HTTP Status: {http_status}
- Error Message: {error_message}
- Attempted Methods: {', '.join(attempted_methods) if attempted_methods else 'Not specified'}
- Fallback Used: {'Yes' if fallback_used else 'No'}

IMPACT:
- Enhanced captions are not available for this posting session
- Basic captions (photo metadata only) are being used as fallback
- Blog content context is missing from Instagram posts

INVESTIGATION STEPS:
1. Check Cloudflare security rules for bot protection settings
2. Verify WordPress REST API is enabled on {blog_url}
3. Check if user-agent 'TravelMemo-ContentFetcher/1.0' needs whitelisting
4. Review server logs for blocked requests
5. Test API endpoint manually: {blog_url}

CLOUDFLARE TROUBLESHOOTING:
- Review Bot Fight Mode settings in Cloudflare dashboard
- Check Page Rules for WordPress API endpoints (/wp-json/*)
- Verify Rate Limiting isn't blocking automation requests
- Consider adding user-agent bypass rule for 'TravelMemo-ContentFetcher/1.0'
- Check if IP whitelisting is needed for GitHub Actions runners

The automation will continue with basic captions until this issue is resolved.

---
Flickr to Instagram Automation System
Generated automatically on {timestamp}
"""

    def _create_api_failure_html_content(self,
                                        blog_url: str,
                                        error_details: dict,
                                        account_name: str) -> str:
        """Create HTML email content for API failure."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M UTC')

        # Extract error information
        http_status = error_details.get('http_status', 'Unknown')
        error_message = error_details.get('error_message', 'No specific error message')
        attempted_methods = error_details.get('attempted_methods', [])
        fallback_used = error_details.get('fallback_used', False)

        return f"""
        <html>
          <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f44336; color: white; padding: 20px; border-radius: 8px; text-align: center;">
              <h1 style="margin: 0;">🚨 WordPress API Access Failure</h1>
              <p style="margin: 10px 0 0 0; font-size: 18px;">{account_name} Account</p>
            </div>

            <div style="padding: 20px; background-color: #ffebee; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f44336;">
              <h2 style="color: #c62828; margin-top: 0;">Error Details</h2>
              <table style="width: 100%; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid #ddd;">
                  <td style="padding: 8px; font-weight: bold;">Time:</td>
                  <td style="padding: 8px;">{timestamp}</td>
                </tr>
                <tr style="border-bottom: 1px solid #ddd;">
                  <td style="padding: 8px; font-weight: bold;">Blog URL:</td>
                  <td style="padding: 8px;"><a href="{blog_url}" style="color: #1976D2;">{blog_url}</a></td>
                </tr>
                <tr style="border-bottom: 1px solid #ddd;">
                  <td style="padding: 8px; font-weight: bold;">HTTP Status:</td>
                  <td style="padding: 8px;"><code>{http_status}</code></td>
                </tr>
                <tr style="border-bottom: 1px solid #ddd;">
                  <td style="padding: 8px; font-weight: bold;">Error Message:</td>
                  <td style="padding: 8px;"><code>{error_message}</code></td>
                </tr>
                <tr style="border-bottom: 1px solid #ddd;">
                  <td style="padding: 8px; font-weight: bold;">Attempted Methods:</td>
                  <td style="padding: 8px;">{', '.join(attempted_methods) if attempted_methods else 'Not specified'}</td>
                </tr>
                <tr>
                  <td style="padding: 8px; font-weight: bold;">Fallback Used:</td>
                  <td style="padding: 8px;">{'✅ Yes' if fallback_used else '❌ No'}</td>
                </tr>
              </table>
            </div>

            <div style="padding: 20px; background-color: #fff3e0; border-radius: 8px; border-left: 4px solid #ff9800;">
              <h3 style="color: #ef6c00; margin-top: 0;">Impact</h3>
              <ul style="color: #333; line-height: 1.6;">
                <li>Enhanced captions are not available for this posting session</li>
                <li>Basic captions (photo metadata only) are being used as fallback</li>
                <li>Blog content context is missing from Instagram posts</li>
              </ul>
            </div>

            <div style="padding: 20px; background-color: #e8f5e8; border-radius: 8px; border-left: 4px solid #4caf50;">
              <h3 style="color: #2e7d32; margin-top: 0;">Investigation Steps</h3>
              <ol style="color: #333; line-height: 1.6;">
                <li><strong>Cloudflare Security:</strong> Check bot protection settings in Cloudflare dashboard</li>
                <li><strong>WordPress API:</strong> Verify REST API is enabled on <a href="{blog_url}">{blog_url}</a></li>
                <li><strong>User-Agent Whitelist:</strong> Check if 'TravelMemo-ContentFetcher/1.0' needs whitelisting</li>
                <li><strong>Server Logs:</strong> Review server logs for blocked requests</li>
                <li><strong>Manual Test:</strong> Test API endpoint manually</li>
              </ol>
            </div>

            <div style="padding: 20px; background-color: #e3f2fd; border-radius: 8px; border-left: 4px solid #2196f3;">
              <h3 style="color: #1976d2; margin-top: 0;">Cloudflare Troubleshooting</h3>
              <ul style="color: #333; line-height: 1.6;">
                <li>Review <strong>Bot Fight Mode</strong> settings</li>
                <li>Check <strong>Page Rules</strong> for WordPress API endpoints (/wp-json/*)</li>
                <li>Verify <strong>Rate Limiting</strong> isn't blocking automation requests</li>
                <li>Consider adding <strong>user-agent bypass rule</strong> for 'TravelMemo-ContentFetcher/1.0'</li>
                <li>Check if <strong>IP whitelisting</strong> is needed for GitHub Actions runners</li>
              </ul>
            </div>

            <div style="text-align: center; margin-top: 30px; padding: 20px; border-top: 1px solid #ddd;">
              <p style="color: #666; font-size: 14px;">
                The automation will continue with basic captions until this issue is resolved.<br>
                Generated automatically by Flickr to Instagram Automation System<br>
                <em>{timestamp}</em>
              </p>
            </div>
          </body>
        </html>
        """

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