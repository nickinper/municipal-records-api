#!/usr/bin/env python3
"""
Generate Personal Injury Law Firm Outreach List
Combines all PI firms and creates actionable outreach plan
"""

import json
import csv
from datetime import datetime

# Top Phoenix PI Firms (from research)
PI_FIRMS = [
    {"name": "Lamber Goodnow Injury Lawyers", "priority": "HIGH", "notes": "Large PI firm, high volume"},
    {"name": "Phillips Law Group", "priority": "HIGH", "notes": "Major PI player, TV advertising"},
    {"name": "Breyer Law Offices", "priority": "HIGH", "notes": "Husband & Wife Law Team brand"},
    {"name": "Husband and Wife Law Team", "priority": "HIGH", "notes": "High visibility, motorcycle focus"},
    {"name": "Zazueta Law", "priority": "HIGH", "notes": "Growing firm, tech-forward"},
    {"name": "Kelly Law Team", "priority": "HIGH", "notes": "Personal injury specialists"},
    {"name": "Stone Rose Law", "priority": "MEDIUM", "notes": "Boutique PI firm"},
    {"name": "Sargon Law Group", "priority": "MEDIUM", "notes": "Auto accident focus"},
    {"name": "The Bundren Law Firm", "priority": "MEDIUM", "notes": "Injury & wrongful death"},
    {"name": "Escamilla Law Group", "priority": "HIGH", "notes": "High volume auto accidents"},
    {"name": "Torgenson Law", "priority": "HIGH", "notes": "Multiple offices, large team"},
    {"name": "Law Offices of Michael Cordova", "priority": "MEDIUM", "notes": "Solo/small firm"},
    {"name": "Rispoli Law", "priority": "MEDIUM", "notes": "Personal injury focus"},
    {"name": "Nolan Law Firm", "priority": "MEDIUM", "notes": "General PI practice"},
    {"name": "Zanes Law", "priority": "HIGH", "notes": "Large firm, multiple locations"},
]

# Insurance defense firms that also handle PI
HYBRID_FIRMS = [
    {"name": "Gallagher & Kennedy", "priority": "HIGH", "notes": "Insurance defense + PI"},
    {"name": "Snell & Wilmer", "priority": "HIGH", "notes": "Major firm with PI practice"},
    {"name": "Lewis Roca", "priority": "HIGH", "notes": "Defense & plaintiff work"},
    {"name": "Jones, Skelton & Hochuli", "priority": "MEDIUM", "notes": "Primarily defense"},
    {"name": "Burch & Cracchiolo", "priority": "MEDIUM", "notes": "PI and insurance"},
]

def generate_email_template(firm_name, firm_type="PI"):
    """Generate personalized email template for firm"""
    
    if firm_type == "PI":
        return f"""
Subject: {firm_name} - Police reports in 48 hours (not 18 months)

Hi [Name],

I noticed {firm_name} handles personal injury cases in Phoenix.

Your paralegals are probably spending hours trying to get police reports from Phoenix PD's 18-month backlog.

We automated their portal. Your reports in 48-72 hours, guaranteed.

What this means for {firm_name}:
• Settle cases 18 months faster
• Take on 30% more cases with same staff
• Stop losing clients to delays

Free trial: We'll get your next police report at no charge.

Worth 15 minutes to see how we can accelerate your settlements?

Best,
[Your name]
(602) 806-8526
"""
    else:
        return f"""
Subject: {firm_name} - Accelerate your PI settlements by 18 months

Hi [Name],

I saw {firm_name} handles injury cases in Phoenix.

Quick question - how many settlements are delayed waiting for Phoenix PD reports?

We get them in 48 hours instead of 18 months. Your cases move faster, clients stay happy.

Recent client result: Settled a $750K case 6 months before statute of limitations expired.

Free pilot program for {firm_name}:
• 5 free reports
• No commitment
• See results this week

15-minute call to discuss?

Best,
[Your name]
"""

def generate_linkedin_searches(firms):
    """Generate LinkedIn search URLs"""
    searches = []
    
    titles = [
        "managing partner",
        "senior partner personal injury",
        "litigation partner",
        "office administrator",
        "legal operations",
        "paralegal manager"
    ]
    
    for firm in firms:
        for title in titles:
            search = {
                "firm": firm["name"],
                "search_query": f'"{title}" "{firm["name"]}" Phoenix',
                "url": f'https://www.linkedin.com/search/results/people/?keywords={title} {firm["name"]} Phoenix'
            }
            searches.append(search)
    
    return searches

def create_outreach_csv(all_firms):
    """Create CSV for tracking outreach"""
    
    filename = f"leads/pi_firm_outreach_{datetime.now().strftime('%Y%m%d')}.csv"
    
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['Company', 'Type', 'Priority', 'Contact_Name', 'Title', 
                     'Email', 'Phone', 'LinkedIn', 'Email_Sent', 'Response', 
                     'Follow_Up_Date', 'Notes']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for firm in all_firms:
            writer.writerow({
                'Company': firm['name'],
                'Type': firm.get('type', 'PI Law Firm'),
                'Priority': firm['priority'],
                'Contact_Name': '',
                'Title': '',
                'Email': '',
                'Phone': '',
                'LinkedIn': '',
                'Email_Sent': '',
                'Response': '',
                'Follow_Up_Date': '',
                'Notes': firm['notes']
            })
    
    return filename

def generate_calling_script():
    """Generate phone script for cold calls"""
    
    return """
PHONE SCRIPT FOR PI LAW FIRMS
=============================

OPENING (Get past gatekeeper):
"Hi, I'm calling about accelerating your police report turnaround from 18 months to 48 hours. 
Who handles your firm's case management operations?"

PITCH (Once connected to decision maker):
"Hi [Name], I'm [Your name] from Municipal Records Processing. 

I know your paralegals spend hours trying to get police reports from Phoenix PD, 
and then wait 18 months for them to arrive.

We've automated their submission system - you get reports in 48 hours instead of 18 months.

[Firm name] could settle cases faster and take on more clients with the same staff.

We're offering a free pilot program - we'll get your next 5 police reports at no charge 
so you can see the time savings firsthand.

Do you have 15 minutes this week to discuss how this could help your firm?"

OBJECTION HANDLERS:

"We already have a process"
→ "I understand. How long does your current process take to get Phoenix PD reports? 
   [Listen] 
   Our clients were waiting 18 months too. Now they get them in 48 hours."

"How much does it cost?"
→ "It's $69 per report, but the free pilot lets you test it risk-free. 
   Most firms save that in paralegal time on just the first report."

"We don't need this"
→ "I appreciate that. Quick question - if you could settle cases 18 months faster, 
   would that help your cash flow? The pilot is free, so there's no risk to trying it."

CLOSING:
"Great! I'll send you an email with the pilot program details. 
What's the best email to reach you?

I'll also include some case studies from other Phoenix PI firms who are using this.

One last question - how many police reports does your firm typically need per month? 
This helps me customize the pilot for your volume."

EMAIL FOLLOW-UP:
Send immediately after call with:
- Pilot program details
- Case study PDF
- Calendar link for demo
"""

def main():
    # Combine all firms
    all_firms = []
    
    # Add PI firms
    for firm in PI_FIRMS:
        firm_data = {
            "name": firm["name"],
            "type": "PI Law Firm",
            "priority": firm["priority"],
            "notes": firm["notes"],
            "email_template": generate_email_template(firm["name"], "PI")
        }
        all_firms.append(firm_data)
    
    # Add hybrid firms
    for firm in HYBRID_FIRMS:
        firm_data = {
            "name": firm["name"],
            "type": "Hybrid (Defense + PI)",
            "priority": firm["priority"],
            "notes": firm["notes"],
            "email_template": generate_email_template(firm["name"], "Hybrid")
        }
        all_firms.append(firm_data)
    
    # Sort by priority
    all_firms.sort(key=lambda x: (x["priority"] != "HIGH", x["name"]))
    
    # Generate outputs
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save firm list with templates
    with open(f'leads/pi_firms_master_list_{timestamp}.json', 'w') as f:
        json.dump(all_firms, f, indent=2)
    
    # Generate LinkedIn searches
    linkedin_searches = generate_linkedin_searches(all_firms)
    with open(f'leads/pi_firms_linkedin_searches_{timestamp}.json', 'w') as f:
        json.dump(linkedin_searches, f, indent=2)
    
    # Create CSV tracker
    csv_file = create_outreach_csv(all_firms)
    
    # Save calling script
    with open(f'leads/pi_firms_calling_script_{timestamp}.txt', 'w') as f:
        f.write(generate_calling_script())
    
    # Generate action plan
    action_plan = f"""
PI LAW FIRM OUTREACH ACTION PLAN
================================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

IMMEDIATE ACTIONS (Today):
1. Start with HIGH priority firms
2. Find contacts on LinkedIn using the search queries
3. Send personalized emails using templates
4. Track all outreach in: {csv_file}

HIGH PRIORITY TARGETS ({sum(1 for f in all_firms if f['priority'] == 'HIGH')} firms):
{chr(10).join(f"  • {f['name']} - {f['notes']}" for f in all_firms if f['priority'] == 'HIGH')}

OUTREACH SEQUENCE:
Day 1: Send initial email
Day 3: LinkedIn connection request
Day 7: Follow-up email if no response
Day 10: Phone call
Day 14: Final email with case study

TRACKING METRICS:
- Response rate target: 15%
- Meeting booking target: 5%
- Pilot signup target: 2-3 firms

FILES GENERATED:
- Master list: pi_firms_master_list_{timestamp}.json
- LinkedIn searches: pi_firms_linkedin_searches_{timestamp}.json
- Tracking CSV: {csv_file}
- Calling script: pi_firms_calling_script_{timestamp}.txt
"""
    
    # Save action plan
    with open(f'leads/pi_firms_action_plan_{timestamp}.txt', 'w') as f:
        f.write(action_plan)
    
    # Print summary
    print("🎯 PI LAW FIRM OUTREACH LIST GENERATED")
    print("=" * 50)
    print(f"\n📊 Summary:")
    print(f"  - Total firms: {len(all_firms)}")
    print(f"  - HIGH priority: {sum(1 for f in all_firms if f['priority'] == 'HIGH')}")
    print(f"  - MEDIUM priority: {sum(1 for f in all_firms if f['priority'] == 'MEDIUM')}")
    print(f"\n📁 Files created in /leads/ directory:")
    print(f"  - pi_firms_master_list_{timestamp}.json")
    print(f"  - pi_firms_linkedin_searches_{timestamp}.json")
    print(f"  - {csv_file}")
    print(f"  - pi_firms_calling_script_{timestamp}.txt")
    print(f"  - pi_firms_action_plan_{timestamp}.txt")
    print(f"\n🚀 Next steps:")
    print("  1. Open the CSV file to track your outreach")
    print("  2. Use LinkedIn searches to find contacts")
    print("  3. Start with HIGH priority firms")
    print("  4. Use the email templates provided")
    print("  5. Track everything in the CSV")
    print("\n💡 Pro tip: Start with Lamber Goodnow, Phillips Law, and Breyer Law")
    print("   These are the largest PI firms with highest case volumes.\n")

if __name__ == "__main__":
    main()