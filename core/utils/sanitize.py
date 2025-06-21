"""
Input sanitization utilities for Phoenix PD's fragile portal.

Phoenix PD's system crashes with special characters < > & #
This module ensures all inputs are safe before submission.
"""

import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


def sanitize_phoenix_input(text: str) -> str:
    """
    Sanitize input text for Phoenix PD portal submission.
    
    Their system rejects forms with < > & # characters.
    
    Args:
        text: Raw input text
        
    Returns:
        Sanitized text safe for submission
    """
    if not text:
        return ""
        
    # Replace dangerous characters
    replacements = {
        '<': '(',
        '>': ')',
        '&': 'and',
        '#': 'number',
        '"': "'",
        '\n': ' ',
        '\r': ' ',
        '\t': ' ',
    }
    
    result = str(text)
    for char, replacement in replacements.items():
        result = result.replace(char, replacement)
        
    # Remove any other non-printable characters
    result = ''.join(char for char in result if char.isprintable() or char == ' ')
    
    # Collapse multiple spaces
    result = re.sub(r'\s+', ' ', result)
    
    return result.strip()


def sanitize_case_number(case_number: str) -> str:
    """
    Sanitize case numbers for Phoenix PD.
    
    Args:
        case_number: Raw case number
        
    Returns:
        Sanitized case number
    """
    if not case_number:
        raise ValueError("Case number cannot be empty")
        
    # Remove all special characters except hyphens and alphanumeric
    sanitized = re.sub(r'[^A-Za-z0-9\-]', '', str(case_number))
    
    # Ensure it's not empty after sanitization
    if not sanitized:
        raise ValueError(f"Case number '{case_number}' contains no valid characters")
        
    return sanitized.upper()


def sanitize_email(email: str) -> str:
    """
    Sanitize email addresses for Phoenix PD.
    
    Args:
        email: Raw email address
        
    Returns:
        Sanitized email address
    """
    if not email:
        return ""
        
    # Basic email validation
    email = str(email).strip().lower()
    
    # Remove dangerous characters but keep @ and .
    email = re.sub(r'[<>&\#]', '', email)
    
    # Validate email format
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        raise ValueError(f"Invalid email format: {email}")
        
    return email


def sanitize_phone(phone: str) -> str:
    """
    Sanitize phone numbers for Phoenix PD.
    
    Args:
        phone: Raw phone number
        
    Returns:
        Sanitized phone number (digits only)
    """
    if not phone:
        return ""
        
    # Extract only digits
    digits = re.sub(r'\D', '', str(phone))
    
    # Validate US phone number length
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]  # Remove country code
        
    if len(digits) != 10:
        raise ValueError(f"Invalid phone number length: {phone}")
        
    return digits


def sanitize_requestor_info(info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize all requestor information fields.
    
    Args:
        info: Dictionary with requestor information
        
    Returns:
        Sanitized dictionary
    """
    sanitized = {}
    
    # Sanitize each field appropriately
    if 'first_name' in info:
        sanitized['first_name'] = sanitize_phoenix_input(info['first_name'])
        
    if 'last_name' in info:
        sanitized['last_name'] = sanitize_phoenix_input(info['last_name'])
        
    if 'email' in info:
        sanitized['email'] = sanitize_email(info['email'])
        
    if 'phone' in info:
        sanitized['phone'] = sanitize_phone(info['phone'])
        
    if 'company' in info:
        sanitized['company'] = sanitize_phoenix_input(info['company'])
        
    if 'address' in info:
        sanitized['address'] = sanitize_phoenix_input(info['address'])
        
    return sanitized


def validate_911_recording_date(incident_date: datetime) -> bool:
    """
    Validate that a 911 recording request is within the 190-day window.
    
    Phoenix PD only keeps 911 recordings for 190 days.
    
    Args:
        incident_date: Date of the incident
        
    Returns:
        True if within window, False otherwise
    """
    if not incident_date:
        return False
        
    # Calculate age in days
    age = datetime.utcnow() - incident_date
    
    return age.days <= 190


def validate_report_type_restrictions(
    report_type: str, 
    request_data: Dict[str, Any]
) -> tuple[bool, Optional[str]]:
    """
    Validate request data against report type restrictions.
    
    Args:
        report_type: Type of report being requested
        request_data: Request information
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # 911 recordings have 190-day limit
    if report_type == "recordings_911":
        incident_date = request_data.get('incident_date')
        if not incident_date:
            return False, "911 recordings require an incident date"
            
        if not validate_911_recording_date(incident_date):
            return False, "911 recordings are only available within 190 days of the incident"
            
    # Body camera and surveillance may require officer info
    if report_type in ["body_camera", "surveillance"]:
        if not request_data.get('case_number') and not request_data.get('officer_badge'):
            return False, f"{report_type} requests require either a case number or officer badge number"
            
    # Calls for service require an address
    if report_type == "calls_for_service":
        if not request_data.get('address'):
            return False, "Calls for service requests require a specific address"
            
    return True, None


def prepare_phoenix_submission(
    report_type: str,
    case_number: str,
    requestor_info: Dict[str, Any],
    additional_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Prepare and sanitize all data for Phoenix PD submission.
    
    Args:
        report_type: Type of report to request
        case_number: Case/incident number
        requestor_info: Requestor contact information
        additional_data: Any additional data required for specific report types
        
    Returns:
        Sanitized data ready for submission
        
    Raises:
        ValueError: If validation fails
    """
    # Combine all data
    all_data = {
        'case_number': case_number,
        **requestor_info,
        **(additional_data or {})
    }
    
    # Validate report type restrictions
    is_valid, error_msg = validate_report_type_restrictions(report_type, all_data)
    if not is_valid:
        raise ValueError(error_msg)
        
    # Sanitize case number
    sanitized_case = sanitize_case_number(case_number)
    
    # Sanitize requestor info
    sanitized_info = sanitize_requestor_info(requestor_info)
    
    # Sanitize any additional data
    sanitized_additional = {}
    if additional_data:
        for key, value in additional_data.items():
            if isinstance(value, str):
                sanitized_additional[key] = sanitize_phoenix_input(value)
            else:
                sanitized_additional[key] = value
                
    return {
        'report_type': report_type,
        'case_number': sanitized_case,
        'requestor_info': sanitized_info,
        'additional_data': sanitized_additional
    }