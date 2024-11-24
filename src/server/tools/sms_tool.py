# Save as: src/server/tools/sms_tool.py

import os
from datetime import datetime
from pathlib import Path

class SMSTool:
    def __init__(self, output_dir: str = "sms_logs"):
        """
        Initialize the SMS Tool.
        
        :param output_dir: Directory path where SMS logs will be stored
        """
        self.output_dir = output_dir
        # Create the output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    async def send_sms(self, phone_number: str, message: str) -> str:
        """
        Simulates sending an SMS by writing to a file.
        
        :param phone_number: The recipient's phone number
        :param message: The message content to be sent
        :return: String confirmation message with the log file path
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sms_{timestamp}.txt"
        filepath = os.path.join(self.output_dir, filename)
        
        content = f"""
                    Timestamp: {datetime.now().isoformat()}
                    To: {phone_number}
                    Message: {message}
                    """
        
        with open(filepath, 'w') as f:
            f.write(content)
            
        return f"SMS message logged to {filepath}"

    async def send_application_success_sms(self, 
                                         phone_number: str,
                                         company_name: str,
                                         position: str,
                                         contact_person: str = None,
                                         next_steps: str = None) -> str:
        """
        Sends a formatted SMS for successful job applications.
        
        :param phone_number: The recipient's phone number
        :param company_name: Name of the company that accepted the application
        :param position: Job position title that was applied for
        :param contact_person: Optional contact person name at the company
        :param next_steps: Optional information about next steps in the process
        :return: String confirmation message with the log file path
        """
        message = f"Great news! {company_name} has responded positively to your application for the {position} position."
        
        if contact_person:
            message += f"\nYour contact person is {contact_person}."
            
        if next_steps:
            message += f"\nNext steps: {next_steps}"
            
        message += "\nCongratulations!"
        
        return await self.send_sms(phone_number, message)
