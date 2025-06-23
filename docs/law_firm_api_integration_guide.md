# Law Firm API Integration Guide

## Quick Start for Personal Injury Law Firms

This guide helps PI law firms integrate our automated police report service with their case management systems.

## Table of Contents
- [Overview](#overview)
- [Supported Platforms](#supported-platforms)
- [API Basics](#api-basics)
- [Integration Examples](#integration-examples)
- [Workflow Automation](#workflow-automation)
- [Best Practices](#best-practices)
- [Support](#support)

## Overview

Our API enables law firms to:
- Submit police report requests directly from case management systems
- Track request status in real-time
- Receive reports automatically when ready
- Maintain complete audit trails for court admissibility

**Key Benefits:**
- Eliminate manual data entry
- Reduce report turnaround from 18 months to 48 hours
- Automatic status updates in your case files
- Bulk processing capabilities

## Supported Platforms

### Native Integrations
- **Clio** - Install from Clio App Directory
- **MyCase** - Available in MyCase Marketplace
- **PracticePanther** - Direct API integration
- **Filevine** - Custom workflow automation

### API Compatible Systems
- Smokeball
- CosmoLex
- Rocket Matter
- Zola Suite
- Custom/proprietary systems

## API Basics

### Authentication
```bash
# All requests require API key in header
Authorization: Bearer YOUR_API_KEY
```

### Base URL
```
https://api.municipalrecordsprocessing.com/v1
```

### Rate Limits
- 100 requests per minute
- 10,000 requests per day
- Bulk endpoints: 50 reports per request

## Integration Examples

### 1. Submit a Police Report Request

**Endpoint:** `POST /api/v1/submit-request`

```python
# Python example for law firms
import requests
import json

API_KEY = "your_api_key_here"
BASE_URL = "https://api.municipalrecordsprocessing.com/v1"

def request_police_report(case_data):
    """Submit a police report request for a PI case"""
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "report_type": "traffic_crash",
        "case_number": case_data["police_case_number"],
        "incident_date": case_data["accident_date"],
        "client_info": {
            "first_name": case_data["client_first_name"],
            "last_name": case_data["client_last_name"],
            "case_reference": case_data["firm_case_id"]  # Your internal case ID
        },
        "delivery_webhook": f"https://yourfirm.com/webhook/reports/{case_data['firm_case_id']}",
        "priority": "standard"  # or "rush" for 24-hour service
    }
    
    response = requests.post(
        f"{BASE_URL}/submit-request",
        headers=headers,
        json=payload
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"Request submitted. Tracking ID: {result['request_id']}")
        return result
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

# Example usage
case_info = {
    "police_case_number": "2024-123456",
    "accident_date": "2024-01-15",
    "client_first_name": "John",
    "client_last_name": "Doe",
    "firm_case_id": "PI-2024-0892"
}

request_police_report(case_info)
```

### 2. Check Request Status

**Endpoint:** `GET /api/v1/status/{request_id}`

```python
def check_report_status(request_id):
    """Check the status of a police report request"""
    
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    response = requests.get(
        f"{BASE_URL}/status/{request_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        status = response.json()
        print(f"Status: {status['status']}")
        print(f"Progress: {status['progress_percentage']}%")
        
        if status['status'] == 'completed':
            print(f"Download URL: {status['download_url']}")
            
        return status
    else:
        print(f"Error checking status: {response.text}")
        return None
```

### 3. Bulk Submit Multiple Requests

**Endpoint:** `POST /api/v1/bulk-submit`

```python
def bulk_submit_reports(cases):
    """Submit multiple police report requests at once"""
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "requests": [
            {
                "report_type": "traffic_crash",
                "case_number": case["police_case_number"],
                "incident_date": case["accident_date"],
                "client_reference": case["firm_case_id"]
            }
            for case in cases
        ]
    }
    
    response = requests.post(
        f"{BASE_URL}/bulk-submit",
        headers=headers,
        json=payload
    )
    
    if response.status_code == 200:
        results = response.json()
        print(f"Submitted {len(results['requests'])} reports")
        return results
    else:
        print(f"Bulk submit error: {response.text}")
        return None
```

## Workflow Automation

### Clio Integration Example

```javascript
// Clio Workflow Automation Script
// Automatically request police reports when case status changes

const CLIO_API_KEY = 'your_clio_api_key';
const MRP_API_KEY = 'your_mrp_api_key';

// Webhook handler for Clio matter updates
async function handleClioWebhook(event) {
    if (event.type === 'matter.updated' && 
        event.data.status === 'Active' && 
        event.data.practice_area === 'Personal Injury') {
        
        // Check if police report is needed
        const customFields = event.data.custom_field_values;
        const needsPoliceReport = customFields.find(
            field => field.field_name === 'Police Report Status'
        )?.value === 'Needed';
        
        if (needsPoliceReport) {
            // Submit report request
            const reportRequest = await submitPoliceReport({
                case_number: customFields.find(f => f.field_name === 'Police Case #')?.value,
                incident_date: customFields.find(f => f.field_name === 'Accident Date')?.value,
                matter_id: event.data.id
            });
            
            // Update Clio matter with tracking info
            await updateClioMatter(event.data.id, {
                'Police Report Status': 'Requested',
                'Report Tracking ID': reportRequest.request_id
            });
        }
    }
}
```

### MyCase Integration Example

```php
// MyCase PHP Integration
// Add to your MyCase custom integration

class PoliceReportAutomation {
    private $mycase_api;
    private $mrp_api_key = 'your_mrp_api_key';
    
    public function requestReportForCase($case_id) {
        // Get case details from MyCase
        $case = $this->mycase_api->getCase($case_id);
        
        if ($case->case_type === 'Personal Injury' && 
            !empty($case->custom_fields->police_case_number)) {
            
            // Submit to Municipal Records Processing
            $request_data = [
                'report_type' => 'traffic_crash',
                'case_number' => $case->custom_fields->police_case_number,
                'incident_date' => $case->incident_date,
                'client_info' => [
                    'first_name' => $case->client->first_name,
                    'last_name' => $case->client->last_name,
                    'case_reference' => $case->case_number
                ],
                'delivery_webhook' => 'https://yourfirm.com/mycase/webhook'
            ];
            
            $response = $this->submitToMRP($request_data);
            
            // Update MyCase with tracking info
            $this->mycase_api->updateCase($case_id, [
                'police_report_status' => 'Requested',
                'report_tracking_id' => $response->request_id
            ]);
            
            // Add note to case
            $this->mycase_api->addNote($case_id, 
                "Police report requested. Tracking ID: {$response->request_id}. 
                Expected delivery: 48-72 hours."
            );
        }
    }
}
```

## Best Practices

### 1. Error Handling
```python
def safe_submit_report(case_data, max_retries=3):
    """Submit report with retry logic"""
    
    for attempt in range(max_retries):
        try:
            result = request_police_report(case_data)
            if result:
                return result
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
    
    return None
```

### 2. Webhook Security
```python
# Verify webhook signatures
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    """Verify that webhook came from Municipal Records Processing"""
    
    expected_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)

# In your webhook handler
@app.route('/webhook/report-ready', methods=['POST'])
def handle_report_webhook():
    signature = request.headers.get('X-MRP-Signature')
    
    if not verify_webhook_signature(request.data, signature, WEBHOOK_SECRET):
        return "Unauthorized", 401
    
    # Process the webhook
    data = request.json
    # Update your case management system
    # Download the report
    # Notify attorneys/paralegals
```

### 3. Batch Processing for High Volume
```python
def process_daily_cases():
    """Process all new PI cases that need police reports"""
    
    # Get cases from your system
    new_cases = get_cases_needing_reports()
    
    # Batch them for efficiency
    batches = [new_cases[i:i+50] for i in range(0, len(new_cases), 50)]
    
    for batch in batches:
        results = bulk_submit_reports(batch)
        
        # Update your case management system
        for result in results['requests']:
            update_case_status(
                result['client_reference'],
                result['request_id'],
                result['status']
            )
        
        # Rate limit compliance
        time.sleep(1)
```

### 4. Status Monitoring
```python
def monitor_pending_reports():
    """Check status of all pending reports"""
    
    pending_requests = get_pending_report_requests()
    
    for request in pending_requests:
        status = check_report_status(request['tracking_id'])
        
        if status['status'] == 'completed':
            # Download report
            download_report(
                status['download_url'],
                request['case_id']
            )
            
            # Update case
            update_case_report_received(
                request['case_id'],
                status['completion_date']
            )
            
            # Notify team
            notify_team_report_ready(request['case_id'])
```

## Common Integration Patterns

### 1. Automatic Request on Case Creation
- Trigger: New PI case created
- Action: Submit police report request
- Update: Add tracking ID to case

### 2. Daily Batch Processing
- Schedule: Run at 9 AM daily
- Action: Submit all pending requests
- Report: Email summary to partners

### 3. Real-time Status Updates
- Method: Webhook notifications
- Action: Update case status
- Alert: Notify assigned attorney

### 4. Document Management Integration
- Receive: Download completed reports
- Store: Save to case documents
- Index: Make searchable in system

## API Response Examples

### Successful Submission
```json
{
    "success": true,
    "request_id": "req_abc123xyz",
    "status": "submitted",
    "estimated_completion": "2024-01-17T15:00:00Z",
    "tracking_url": "https://portal.municipalrecordsprocessing.com/track/req_abc123xyz"
}
```

### Status Check Response
```json
{
    "request_id": "req_abc123xyz",
    "status": "in_progress",
    "progress_percentage": 75,
    "status_history": [
        {
            "status": "submitted",
            "timestamp": "2024-01-15T10:00:00Z"
        },
        {
            "status": "processing",
            "timestamp": "2024-01-15T10:05:00Z"
        }
    ],
    "estimated_completion": "2024-01-17T15:00:00Z"
}
```

### Completed Report
```json
{
    "request_id": "req_abc123xyz",
    "status": "completed",
    "progress_percentage": 100,
    "completion_date": "2024-01-17T14:30:00Z",
    "download_url": "https://secure.municipalrecordsprocessing.com/download/req_abc123xyz",
    "download_expires": "2024-01-24T14:30:00Z",
    "report_details": {
        "pages": 15,
        "format": "PDF",
        "size_bytes": 2457600
    }
}
```

## Testing Your Integration

### Test API Endpoint
```
https://sandbox.municipalrecordsprocessing.com/v1
```

### Test Credentials
- API Key: `test_pk_abc123xyz`
- Use case numbers starting with "TEST-" for sandbox

### Sample Test Cases
```python
# Test successful submission
test_case_1 = {
    "police_case_number": "TEST-SUCCESS-001",
    "accident_date": "2024-01-01",
    "client_first_name": "Test",
    "client_last_name": "Success"
}

# Test delayed response
test_case_2 = {
    "police_case_number": "TEST-DELAY-001",
    # Will complete after 5 minutes
}

# Test failure case
test_case_3 = {
    "police_case_number": "TEST-FAIL-001",
    # Will return not_found status
}
```

## Support

### Developer Resources
- API Documentation: https://api.municipalrecordsprocessing.com/docs
- Postman Collection: [Download](https://api.municipalrecordsprocessing.com/postman)
- Status Page: https://status.municipalrecordsprocessing.com

### Technical Support
- Email: api-support@municipalrecordsprocessing.com
- Phone: (602) 806-8526 ext. 2
- Slack: Join our developer community

### Integration Assistance
- Free integration consultation for law firms
- Custom development services available
- Training webinars monthly

## Appendix: Case Management System Specifics

### Clio
- App Directory listing: "Municipal Records Automation"
- Required scopes: matters.read, matters.write, webhooks
- Setup time: 10 minutes

### MyCase
- Integration type: Custom API
- Required permissions: Case management, Document upload
- Setup guide: [Link]

### PracticePanther
- Integration method: REST API
- Authentication: OAuth 2.0
- Webhook support: Yes

### Filevine
- Integration type: Native workflow
- Required plan: Business or above
- Custom fields needed: 3

---

*Last updated: January 2024*
*Version: 1.0*